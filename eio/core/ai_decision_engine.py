"""
AI Decision Engine
===================
Replaces the simple ModelRouter with a full multi-criteria evaluation engine.

For every request the Decision Engine:
  1. Reads the RoutingContext produced by the Planner
  2. Queries the ModelCapabilityRegistry for candidate models
  3. Scores each candidate on 7 dimensions
  4. Applies PolicyEngine governance constraints
  5. Skips models marked offline by ModelHealthRegistry
  6. Returns a rich AIDecisionResult that is surfaced in the UI

Scoring dimensions (each 0.0 – 1.0, weighted):
  reasoning_capability  0.25
  sql_capability        0.20  (only relevant when sql_needed)
  long_context          0.10  (only relevant when rag_needed)
  governance_compliance 0.20
  cost_efficiency       0.15
  latency               0.10

The score is normalized to 0–100 and attached to every candidate
so the UI can show exactly why the winning model was chosen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eio.connectors.llm.base import RoutingContext, RoutingDecision
from eio.core.model_capability_registry import (
    ModelCapabilityProfile,
    ModelCapabilityRegistry,
)
from eio.core.model_health_registry import ModelHealthRegistry


@dataclass
class CandidateScore:
    """Score breakdown for a single candidate model."""
    profile:             ModelCapabilityProfile
    reasoning_score:     float = 0.0
    sql_score:           float = 0.0
    context_score:       float = 0.0
    governance_score:    float = 0.0
    cost_score:          float = 0.0
    latency_score:       float = 0.0
    total_score:         float = 0.0        # 0 – 100
    disqualified:        bool  = False
    disqualify_reason:   str   = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":         self.profile.model_id,
            "display_name":     self.profile.display_name,
            "provider":         self.profile.provider,
            "capabilities":     self.profile.capability_tags(),
            "context_window":   self.profile.context_window,
            "cost_per_1k_in":   self.profile.cost_per_1k_input,
            "cost_per_1k_out":  self.profile.cost_per_1k_output,
            "avg_latency_ms":   self.profile.avg_latency_ms,
            "scores": {
                "reasoning":    round(self.reasoning_score * 100, 1),
                "sql":          round(self.sql_score * 100, 1),
                "long_context": round(self.context_score * 100, 1),
                "governance":   round(self.governance_score * 100, 1),
                "cost":         round(self.cost_score * 100, 1),
                "latency":      round(self.latency_score * 100, 1),
            },
            "total_score":      round(self.total_score, 1),
            "disqualified":     self.disqualified,
            "disqualify_reason": self.disqualify_reason,
            "notes":            self.profile.notes,
        }


@dataclass
class TaskModelAssignment:
    """Task-level model routing — different models for different pipeline stages."""
    stage:        str    # "planning" | "sql_generation" | "reasoning" | "synthesis"
    model_id:     str
    display_name: str
    provider:     str
    reason:       str


@dataclass
class AIDecisionResult:
    """Full output of the AI Decision Engine — surfaced directly in the UI."""

    # Request context
    request_complexity:   str = "medium"
    business_intent:      str = ""
    required_capabilities: list[str] = field(default_factory=list)
    estimated_tokens:     int = 0
    estimated_cost_usd:   float = 0.0

    # Candidates evaluated
    candidates_evaluated:  list[CandidateScore] = field(default_factory=list)

    # Winner
    selected_model_id:    str = ""
    selected_provider:    str = ""
    selected_display_name: str = ""
    selection_confidence: float = 0.0
    selection_reason:     str = ""
    policy_applied:       list[str] = field(default_factory=list)

    # Task-level routing (enhancement #6)
    task_assignments:     list[TaskModelAssignment] = field(default_factory=list)

    # Converted to RoutingDecision for compatibility with existing orchestrator
    routing_decision:     RoutingDecision | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_complexity":    self.request_complexity,
            "business_intent":       self.business_intent,
            "required_capabilities": self.required_capabilities,
            "estimated_tokens":      self.estimated_tokens,
            "estimated_cost_usd":    round(self.estimated_cost_usd, 6),
            "candidates_evaluated":  [c.to_dict() for c in self.candidates_evaluated],
            "selected_model_id":     self.selected_model_id,
            "selected_provider":     self.selected_provider,
            "selected_display_name": self.selected_display_name,
            "selection_confidence":  round(self.selection_confidence, 1),
            "selection_reason":      self.selection_reason,
            "policy_applied":        self.policy_applied,
            "task_assignments":      [
                {
                    "stage":        t.stage,
                    "model_id":     t.model_id,
                    "display_name": t.display_name,
                    "provider":     t.provider,
                    "reason":       t.reason,
                }
                for t in self.task_assignments
            ],
        }


# ── Scoring weights ────────────────────────────────────────────────────────

_WEIGHTS = {
    "reasoning":   0.25,
    "sql":         0.20,
    "context":     0.10,
    "governance":  0.20,
    "cost":        0.15,
    "latency":     0.10,
}

# Maximum cost / latency used for normalization
_MAX_COST_PER_1K    = 0.05
_MAX_LATENCY_MS     = 10_000


class AIDecisionEngine:
    """
    Multi-criteria model evaluation engine.
    Replaces the simple ModelRouter with full transparent scoring.
    """

    def __init__(
        self,
        approved_models: list[str] | None = None,
        max_cost_usd: float = 0.50,
        max_tokens: int = 16_000,
    ) -> None:
        self._approved = set(approved_models) if approved_models else None
        self._max_cost  = max_cost_usd
        self._max_tokens = max_tokens

    def evaluate(self, context: RoutingContext) -> AIDecisionResult:
        """
        Full evaluation pipeline:
          1. Build candidate list from ModelCapabilityRegistry
          2. Disqualify models that fail hard constraints
          3. Score remaining candidates
          4. Select winner
          5. Build task-level assignments
          6. Return AIDecisionResult
        """
        result = AIDecisionResult(
            request_complexity=context.complexity,
            business_intent=context.user_query[:120],
            estimated_tokens=context.estimated_tokens,
        )

        # Required capabilities from context
        required_caps = self._required_capabilities(context)
        result.required_capabilities = required_caps

        # Estimated cost at max tier (gpt-4o) for budget check
        from eio.core.llm_pricing import tokens_to_cost
        result.estimated_cost_usd = tokens_to_cost("gpt-4o", context.estimated_tokens)

        # Build + score candidates
        all_profiles = ModelCapabilityRegistry.all()
        if not all_profiles:
            # Registry not populated yet — fall back to simple routing
            return self._simple_fallback(context, result)

        scored: list[CandidateScore] = []
        for profile in all_profiles:
            cs = self._score(profile, context, required_caps)
            scored.append(cs)

        result.candidates_evaluated = scored

        # Select best non-disqualified candidate
        eligible = [c for c in scored if not c.disqualified]
        if not eligible:
            eligible = scored  # all disqualified → pick best anyway

        winner = max(eligible, key=lambda c: c.total_score)
        result.selected_model_id    = winner.profile.model_id
        result.selected_provider    = winner.profile.provider
        result.selected_display_name = winner.profile.display_name
        result.selection_confidence = winner.total_score
        result.selection_reason     = self._build_reason(winner, context)
        result.policy_applied       = self._policy_tags(context)

        # Build RoutingDecision for backward compatibility
        result.routing_decision = RoutingDecision(
            provider=winner.profile.provider,
            model=winner.profile.model_id,
            reason=result.selection_reason,
            estimated_cost_usd=result.estimated_cost_usd,
            estimated_tokens=context.estimated_tokens,
            complexity=context.complexity,
            policy_applied=result.policy_applied,
        )

        # Task-level routing (Enhancement #6)
        result.task_assignments = self._task_assignments(context, scored)

        return result

    # ── Private helpers ────────────────────────────────────────────────

    def _score(
        self,
        profile: ModelCapabilityProfile,
        context: RoutingContext,
        required_caps: list[str],
    ) -> CandidateScore:
        cs = CandidateScore(profile=profile)

        # Hard disqualification checks
        if self._approved and profile.model_id not in self._approved:
            cs.disqualified = True
            cs.disqualify_reason = "Not in approved model list (policy)"
            return cs

        health = ModelHealthRegistry.get(profile.model_id)
        if health and not health.available:
            cs.disqualified = True
            cs.disqualify_reason = f"Model offline: {health.last_error_msg}"
            return cs

        if context.sql_needed and not profile.sql_generation:
            cs.disqualified = True
            cs.disqualify_reason = "SQL generation required but not supported"
            return cs

        if context.estimated_tokens > profile.context_window * 0.9:
            cs.disqualified = True
            cs.disqualify_reason = (
                f"Context window too small: need {context.estimated_tokens}, "
                f"model supports {profile.context_window}"
            )
            return cs

        # Compute dimension scores
        cs.reasoning_score = profile.reasoning_score
        cs.sql_score       = profile.sql_score if context.sql_needed else 1.0
        cs.context_score   = 1.0 if profile.long_context else 0.5

        cs.governance_score = 1.0 if profile.governance_approved else 0.0

        # Cost score: lower cost = higher score
        blended = profile.cost_per_1k_input * 0.7 + profile.cost_per_1k_output * 0.3
        cs.cost_score = max(0.0, 1.0 - (blended / _MAX_COST_PER_1K))

        # Latency score: lower latency = higher score
        cs.latency_score = max(0.0, 1.0 - (profile.avg_latency_ms / _MAX_LATENCY_MS))

        # Weighted total (0 – 100)
        cs.total_score = (
            cs.reasoning_score  * _WEIGHTS["reasoning"] +
            cs.sql_score        * _WEIGHTS["sql"] +
            cs.context_score    * _WEIGHTS["context"] +
            cs.governance_score * _WEIGHTS["governance"] +
            cs.cost_score       * _WEIGHTS["cost"] +
            cs.latency_score    * _WEIGHTS["latency"]
        ) * 100

        return cs

    @staticmethod
    def _required_capabilities(context: RoutingContext) -> list[str]:
        caps = ["Multi-step Reasoning"]
        if context.sql_needed:
            caps.extend(["SQL Generation", "Structured Output"])
        if context.rag_needed:
            caps.extend(["RAG Support", "Long Context"])
        if context.requires_code_gen:
            caps.append("Code Generation")
        if context.complexity == "high" or context.multi_agent:
            caps.append("Function Calling")
        return list(dict.fromkeys(caps))  # deduplicate preserving order

    @staticmethod
    def _build_reason(winner: CandidateScore, context: RoutingContext) -> str:
        reasons = []
        if context.sql_needed:
            reasons.append(f"SQL accuracy score {winner.sql_score * 100:.0f}/100")
        if winner.profile.governance_approved:
            reasons.append("governance approved")
        reasons.append(f"reasoning score {winner.reasoning_score * 100:.0f}/100")
        reasons.append(f"cost efficiency {winner.cost_score * 100:.0f}/100")
        reasons.append(
            f"overall score {winner.total_score:.1f}/100 — "
            f"highest among {winner.profile.provider} candidates"
        )
        return "; ".join(reasons)

    @staticmethod
    def _policy_tags(context: RoutingContext) -> list[str]:
        tags = []
        if context.sensitive_data:
            tags.append("sensitive_data_restricted")
        if context.complexity == "low":
            tags.append("cost_optimized")
        if context.sql_needed:
            tags.append("sql_accuracy_prioritized")
        return tags

    def _task_assignments(
        self,
        context: RoutingContext,
        scored: list[CandidateScore],
    ) -> list[TaskModelAssignment]:
        """
        Enhancement #6: assign different models to different pipeline stages.
        - Planner: lightweight (fastest, cheapest)
        - SQL Generation: highest SQL score
        - Reasoning / Synthesis: highest reasoning score
        """
        eligible = [c for c in scored if not c.disqualified]
        if not eligible:
            return []

        # Cheapest eligible model for lightweight tasks
        cheapest = min(eligible, key=lambda c: c.profile.cost_per_1k_input)
        # Best SQL model
        best_sql = max(eligible, key=lambda c: c.sql_score)
        # Best reasoning model
        best_reason = max(eligible, key=lambda c: c.reasoning_score)

        assignments = [
            TaskModelAssignment(
                stage="planning",
                model_id=cheapest.profile.model_id,
                display_name=cheapest.profile.display_name,
                provider=cheapest.profile.provider,
                reason="Low-complexity intent classification; cheapest eligible model",
            ),
        ]
        if context.sql_needed:
            assignments.append(TaskModelAssignment(
                stage="sql_generation",
                model_id=best_sql.profile.model_id,
                display_name=best_sql.profile.display_name,
                provider=best_sql.profile.provider,
                reason=f"Highest SQL score ({best_sql.sql_score * 100:.0f}/100); accuracy critical",
            ))
        if context.rag_needed:
            assignments.append(TaskModelAssignment(
                stage="evidence_aggregation",
                model_id=best_reason.profile.model_id,
                display_name=best_reason.profile.display_name,
                provider=best_reason.profile.provider,
                reason="RAG synthesis requires strong long-context reasoning",
            ))
        assignments.append(TaskModelAssignment(
            stage="response_synthesis",
            model_id=best_reason.profile.model_id,
            display_name=best_reason.profile.display_name,
            provider=best_reason.profile.provider,
            reason=f"Complex synthesis; highest reasoning score ({best_reason.reasoning_score * 100:.0f}/100)",
        ))
        return assignments

    @staticmethod
    def _simple_fallback(context: RoutingContext, result: AIDecisionResult) -> AIDecisionResult:
        """Fallback when registry is empty."""
        result.selected_model_id = "gpt-4o"
        result.selected_provider = "openai"
        result.selected_display_name = "GPT-4o (fallback)"
        result.selection_reason = "Capability registry empty — default to GPT-4o"
        result.selection_confidence = 50.0
        result.routing_decision = RoutingDecision(
            provider="openai", model="gpt-4o",
            reason=result.selection_reason,
            estimated_cost_usd=0.01,
            estimated_tokens=context.estimated_tokens,
            complexity=context.complexity,
        )
        return result
