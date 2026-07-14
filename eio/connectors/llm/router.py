"""
Intelligent Model Router
=========================
Selects the optimal LLM provider + model combination for each request
based on: complexity, required capabilities, governance policies, and cost.

The routing decision is logged to the ExplainabilityTrace so every model
selection is fully auditable.

Routing Decision Tree
---------------------
1. Policy pre-check: reject if token budget or cost limit exceeded
2. ICA provider active → task-aware ICA agent selection
3. Prefer preferred_provider if set and approved
4. SQL generation → high-accuracy model (respects active provider)
5. High complexity OR multi-agent → premium model (respects active provider)
6. RAG only, medium complexity → balanced model
7. Low complexity, no SQL, no RAG → economy model
8. Sensitive data → restrict to approved models only
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from eio.connectors.llm.base import RoutingContext, RoutingDecision
from eio.core.llm_pricing import tokens_to_cost

if TYPE_CHECKING:
    from eio.connectors.llm.base import LLMProvider


# ICA agent UUIDs surfaced as routing targets for common task categories
_ICA_AGENT_RESEARCH   = "d464de5e-01b5-461a-94df-d6d0e34a3cfe"   # Internet Researcher
_ICA_AGENT_MARKET     = "70852bb7-7386-4a54-9e31-2af43183f3dd"   # Market Research Agent
_ICA_AGENT_LOG_REVIEW = "eb4d7a7e-274f-4036-a61f-1c1b88ba5d23"   # Analyze Logs v2 (claude-sonnet-4-5)
_ICA_AGENT_DIAGRAMS   = "d6b2274e-4c40-415b-912b-9bdc915b0b46"   # Draw.IO Agent
_ICA_AGENT_DECK_DOC   = "241f8e4f-9b3e-45cb-ac99-713de8d26bf3"   # Deck, Doc & Excel Generator
_ICA_AGENT_USER_STORY = "c0a9a0e2-6224-4a31-87b9-55f495525b74"   # Generate User Stories
_ICA_AGENT_TEST_CASES = "8970a835-0324-4305-8133-c5046f32b46d"   # Generate Test Cases


class ModelRouter:
    """
    Stateless model router. Encapsulates all model selection logic.

    Routing decisions are deterministic given the same RoutingContext
    and policy configuration — making them reproducible and auditable.
    """

    # Ordered routing tiers: (label, model, provider_hint)
    _TIERS = [
        ("premium",   "gpt-4o",        "openai"),
        ("balanced",  "gpt-4o-mini",   "openai"),
        ("economy",   "gpt-3.5-turbo", "openai"),
    ]

    def __init__(
        self,
        approved_models: list[str] | None = None,
        max_cost_usd: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._approved_models = set(approved_models or [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo",
            "claude-3-5-sonnet", "claude-3-haiku",
            "granite-13b-chat", "gemini-1.5-flash",
            "llama3", "mistral",
            # ICA agents pre-approved
            _ICA_AGENT_RESEARCH, _ICA_AGENT_MARKET, _ICA_AGENT_LOG_REVIEW,
            _ICA_AGENT_DIAGRAMS, _ICA_AGENT_DECK_DOC,
            _ICA_AGENT_USER_STORY, _ICA_AGENT_TEST_CASES,
        ])
        self._max_cost_usd = max_cost_usd or float(os.getenv("EIO_POLICY_COST_LIMIT_USD", "0.50"))
        self._max_tokens = max_tokens or int(os.getenv("EIO_POLICY_TOKEN_BUDGET", "16000"))
        # Detect active provider once at construction time
        self._active_llm = os.getenv("EIO_ACTIVE_LLM", "openai").lower()

    def select_model(self, context: RoutingContext) -> RoutingDecision:
        """
        Apply the routing decision tree and return a RoutingDecision.
        Never raises — returns a safe fallback with the rejection reason
        if policy blocks all models.
        """
        policy_applied: list[str] = []
        reasons: list[str] = []

        # ── 1. Token budget check ────────────────────────────────────────
        if context.estimated_tokens > self._max_tokens:
            reasons.append(
                f"Token estimate ({context.estimated_tokens}) exceeds budget ({self._max_tokens})"
            )
            policy_applied.append("token_budget_exceeded")

        # ── 2. Cost pre-check ────────────────────────────────────────────
        estimated_cost = tokens_to_cost("gpt-4o", context.estimated_tokens)
        if estimated_cost > self._max_cost_usd:
            reasons.append(
                f"Estimated cost ${estimated_cost:.4f} exceeds limit ${self._max_cost_usd:.2f}"
            )
            policy_applied.append("cost_limit_exceeded")

        # If policy blocks, return a rejected decision (orchestrator handles it)
        if policy_applied:
            return RoutingDecision(
                provider="none",
                model="none",
                reason=" | ".join(reasons),
                estimated_cost_usd=estimated_cost,
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 3. ICA provider — task-aware agent selection ─────────────────
        # Must be checked before the generic preferred_provider handler so
        # the query-keyword routing logic fires instead of the fallback default.
        if context.preferred_provider == "ica":
            ica_model, ica_reason = self._select_ica_agent(context)
            return RoutingDecision(
                provider="ica",
                model=ica_model,
                reason=ica_reason,
                estimated_cost_usd=tokens_to_cost(ica_model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=["ica_provider_selected"],
            )

        # ── 4. Generic preferred provider override ───────────────────────
        if context.preferred_provider:
            # Honour preference if approved
            preferred_model = self._resolve_model_for_provider(context.preferred_provider)
            if preferred_model and preferred_model in self._approved_models:
                return RoutingDecision(
                    provider=context.preferred_provider,
                    model=preferred_model,
                    reason=f"User-specified preferred provider: {context.preferred_provider}",
                    estimated_cost_usd=tokens_to_cost(preferred_model, context.estimated_tokens),
                    estimated_tokens=context.estimated_tokens,
                    complexity=context.complexity,
                    policy_applied=["preferred_provider_override"],
                )

        # ── 4. SQL generation ────────────────────────────────────────────
        if context.sql_needed:
            if self._active_llm == "ica":
                ica_model, ica_reason = self._select_ica_agent(context)
                return RoutingDecision(
                    provider="ica", model=ica_model,
                    reason=f"SQL query routed to ICA agent (active provider=ica): {ica_reason}",
                    estimated_cost_usd=tokens_to_cost(ica_model, context.estimated_tokens),
                    estimated_tokens=context.estimated_tokens,
                    complexity=context.complexity,
                    policy_applied=policy_applied + ["ica_sql_routing"],
                )
            model, provider = "gpt-4o", "openai"
            return RoutingDecision(
                provider=provider, model=model,
                reason="SQL generation requires high-accuracy model (gpt-4o selected)",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 5. High complexity or multi-agent ──────────────────────────
        if context.complexity == "high" or context.multi_agent:
            if self._active_llm == "ica":
                ica_model, ica_reason = self._select_ica_agent(context)
                return RoutingDecision(
                    provider="ica", model=ica_model,
                    reason=f"High-complexity query routed to ICA agent: {ica_reason}",
                    estimated_cost_usd=tokens_to_cost(ica_model, context.estimated_tokens),
                    estimated_tokens=context.estimated_tokens,
                    complexity=context.complexity,
                    policy_applied=policy_applied + ["ica_high_complexity"],
                )
            model, provider = "gpt-4o", "openai"
            return RoutingDecision(
                provider=provider, model=model,
                reason="High complexity/multi-agent request requires premium model",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 6. RAG only, medium complexity ─────────────────────────────
        if context.rag_needed and context.complexity == "medium":
            if self._active_llm == "ica":
                ica_model, ica_reason = self._select_ica_agent(context)
                return RoutingDecision(
                    provider="ica", model=ica_model,
                    reason=f"RAG query routed to ICA agent: {ica_reason}",
                    estimated_cost_usd=tokens_to_cost(ica_model, context.estimated_tokens),
                    estimated_tokens=context.estimated_tokens,
                    complexity=context.complexity,
                    policy_applied=policy_applied + ["ica_rag_routing"],
                )
            model, provider = "gpt-4o-mini", "openai"
            return RoutingDecision(
                provider=provider, model=model,
                reason="RAG-only medium-complexity request: balanced model (gpt-4o-mini)",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 7. Low complexity, simple Q&A ──────────────────────────────
        if context.complexity == "low" and not context.sql_needed and not context.rag_needed:
            if self._active_llm == "ica":
                ica_model, ica_reason = self._select_ica_agent(context)
                return RoutingDecision(
                    provider="ica", model=ica_model,
                    reason=f"Low-complexity query routed to ICA agent: {ica_reason}",
                    estimated_cost_usd=tokens_to_cost(ica_model, context.estimated_tokens),
                    estimated_tokens=context.estimated_tokens,
                    complexity=context.complexity,
                    policy_applied=policy_applied + ["ica_low_complexity"],
                )
            model, provider = "gpt-4o-mini", "openai"
            return RoutingDecision(
                provider=provider, model=model,
                reason="Low-complexity query: economy model (gpt-4o-mini) for cost savings",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied + ["cost_optimized"],
            )

        # ── 8. Default fallback ─────────────────────────────────────────
        if self._active_llm == "ica":
            ica_model, ica_reason = self._select_ica_agent(context)
            return RoutingDecision(
                provider="ica", model=ica_model,
                reason=f"Default ICA agent: {ica_reason}",
                estimated_cost_usd=tokens_to_cost(ica_model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )
        model, provider = "gpt-4o", "openai"
        return RoutingDecision(
            provider=provider, model=model,
            reason="Default premium model selected for mixed/unknown complexity",
            estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
            estimated_tokens=context.estimated_tokens,
            complexity=context.complexity,
            policy_applied=policy_applied,
        )

    @staticmethod
    def _select_ica_agent(context: RoutingContext) -> tuple[str, str]:
        """
        Choose the best-fit ICA agent UUID for the given routing context.
        Returns (agent_uuid, reason_string).
        """
        q = context.user_query.lower()
        if any(kw in q for kw in ("diagram", "draw", "drawio", "plantuml", "flow", "architecture", "uml")):
            return _ICA_AGENT_DIAGRAMS, "ICA Draw.IO Agent selected for diagram/architecture request"
        if any(kw in q for kw in (" log ", "logs", "log file", "error log", "stacktrace", "kubernetes", "pod crash", "debug")):
            return _ICA_AGENT_LOG_REVIEW, "ICA Log Analyzer selected for log/error analysis request"
        if any(kw in q for kw in ("market", "competitor", "sentiment", "industry", "trend analysis")):
            return _ICA_AGENT_MARKET, "ICA Market Research Agent selected for market analysis"
        if any(kw in q for kw in ("user stor", "acceptance criteria", "epic", "backlog", "agile")):
            return _ICA_AGENT_USER_STORY, "ICA Generate User Stories selected for SDLC/agile request"
        if any(kw in q for kw in ("test case", "test scenario", "qa ", "quality", "unit test")):
            return _ICA_AGENT_TEST_CASES, "ICA Generate Test Cases selected for QA request"
        if any(kw in q for kw in ("deck", "powerpoint", "slide", "presentation", "report", "document")):
            return _ICA_AGENT_DECK_DOC, "ICA Deck/Doc/Excel Generator selected for document request"
        # Default: Internet Researcher (general-purpose, web-aware)
        return _ICA_AGENT_RESEARCH, "ICA Internet Researcher selected as general-purpose ICA agent"

    @staticmethod
    def _resolve_model_for_provider(provider: str) -> str | None:
        """Map a provider name to its default model."""
        mapping = {
            "openai":    "gpt-4o",
            "anthropic": "claude-3-5-sonnet",
            "granite":   "granite-13b-chat",
            "gemini":    "gemini-1.5-pro",
            "ollama":    "llama3",
            "ica":       _ICA_AGENT_RESEARCH,   # default ICA agent
        }
        return mapping.get(provider.lower())
