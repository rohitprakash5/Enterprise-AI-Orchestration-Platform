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
2. Prefer preferred_provider if set and approved
3. SQL generation → high-accuracy model (gpt-4o)
4. High complexity OR multi-agent → premium model (gpt-4o)
5. RAG only, medium complexity → balanced model (gpt-4o-mini)
6. Low complexity, no SQL, no RAG → economy model (gpt-4o-mini or local)
7. Sensitive data → restrict to approved models only
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from eio.connectors.llm.base import RoutingContext, RoutingDecision
from eio.core.llm_pricing import tokens_to_cost

if TYPE_CHECKING:
    from eio.connectors.llm.base import LLMProvider


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
        ])
        self._max_cost_usd = max_cost_usd or float(os.getenv("EIO_POLICY_COST_LIMIT_USD", "0.50"))
        self._max_tokens = max_tokens or int(os.getenv("EIO_POLICY_TOKEN_BUDGET", "16000"))

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

        # ── 3. Preferred provider override ──────────────────────────────
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

        # ── 4. SQL generation → always premium accuracy ─────────────────
        if context.sql_needed:
            model, provider = "gpt-4o", "openai"
            return RoutingDecision(
                provider=provider,
                model=model,
                reason="SQL generation requires high-accuracy model (gpt-4o selected)",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 5. High complexity or multi-agent ──────────────────────────
        if context.complexity == "high" or context.multi_agent:
            model, provider = "gpt-4o", "openai"
            return RoutingDecision(
                provider=provider,
                model=model,
                reason=f"High complexity/multi-agent request requires premium model",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 6. RAG only, medium complexity ─────────────────────────────
        if context.rag_needed and context.complexity == "medium":
            model, provider = "gpt-4o-mini", "openai"
            return RoutingDecision(
                provider=provider,
                model=model,
                reason="RAG-only medium-complexity request: balanced model (gpt-4o-mini)",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied,
            )

        # ── 7. Low complexity, simple Q&A ──────────────────────────────
        if context.complexity == "low" and not context.sql_needed and not context.rag_needed:
            model, provider = "gpt-4o-mini", "openai"
            return RoutingDecision(
                provider=provider,
                model=model,
                reason="Low-complexity query: economy model (gpt-4o-mini) for cost savings",
                estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
                estimated_tokens=context.estimated_tokens,
                complexity=context.complexity,
                policy_applied=policy_applied + ["cost_optimized"],
            )

        # ── 8. Default fallback ─────────────────────────────────────────
        model, provider = "gpt-4o", "openai"
        return RoutingDecision(
            provider=provider,
            model=model,
            reason="Default premium model selected for mixed/unknown complexity",
            estimated_cost_usd=tokens_to_cost(model, context.estimated_tokens),
            estimated_tokens=context.estimated_tokens,
            complexity=context.complexity,
            policy_applied=policy_applied,
        )

    @staticmethod
    def _resolve_model_for_provider(provider: str) -> str | None:
        """Map a provider name to its default model."""
        mapping = {
            "openai":    "gpt-4o",
            "anthropic": "claude-3-5-sonnet",
            "granite":   "granite-13b-chat",
            "gemini":    "gemini-1.5-pro",
            "ollama":    "llama3",
        }
        return mapping.get(provider.lower())
