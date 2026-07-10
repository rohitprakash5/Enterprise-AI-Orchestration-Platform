"""
Model Capability Registry
===========================
Each LLM provider registers a ModelCapabilityProfile that describes
what the model can do, how much it costs, and its performance characteristics.

The Planner uses this registry to:
  1. Find all models that satisfy the required capabilities
  2. Score each candidate on cost / latency / accuracy / governance
  3. Produce a transparent AI Decision Engine output

Adding a new model: call ModelCapabilityRegistry.register(profile) — zero other changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelCapabilityProfile:
    """
    Advertised capabilities and performance characteristics for a single LLM.
    Models self-report this profile; the Planner uses it for selection.
    """

    # Identity
    provider:    str          # "openai" | "gpt_oss" | "anthropic" | "granite" | "gemini" | "ollama" | "mock"
    model_id:    str          # "gpt-4o", "openai/gpt-oss-20b", etc.
    display_name: str         # Human-readable label for UI

    # Capability flags
    sql_generation:      bool = False
    function_calling:    bool = False
    structured_output:   bool = False
    long_context:        bool = False      # context window > 32k tokens
    vision:              bool = False
    code_generation:     bool = False
    multi_step_reasoning: bool = False
    rag_support:         bool = False
    streaming:           bool = False
    embedding:           bool = False

    # Quantitative attributes
    context_window:      int   = 4096     # max tokens
    cost_per_1k_input:   float = 0.0      # USD
    cost_per_1k_output:  float = 0.0      # USD
    avg_latency_ms:      float = 1000.0   # estimated ms per request
    governance_approved: bool  = True     # passes enterprise policy

    # Capability scores (0.0 – 1.0) used by the scoring matrix
    reasoning_score:     float = 0.5      # general reasoning ability
    sql_score:           float = 0.0      # SQL accuracy benchmark
    accuracy_score:      float = 0.5      # general benchmark accuracy

    # Access
    requires_api_key:    bool  = True
    local_only:          bool  = False    # runs on local hardware

    # Metadata
    notes: str = ""

    def capability_tags(self) -> list[str]:
        tags = []
        if self.sql_generation:      tags.append("SQL Generation")
        if self.function_calling:    tags.append("Function Calling")
        if self.structured_output:   tags.append("Structured Output")
        if self.long_context:        tags.append("Long Context")
        if self.vision:              tags.append("Vision")
        if self.code_generation:     tags.append("Code Generation")
        if self.multi_step_reasoning: tags.append("Multi-step Reasoning")
        if self.rag_support:         tags.append("RAG Support")
        if self.streaming:           tags.append("Streaming")
        if self.embedding:           tags.append("Embedding")
        return tags


class ModelCapabilityRegistry:
    """
    Central registry of all model capability profiles.
    The AI Decision Engine queries this to build the candidate list.
    """

    _profiles: dict[str, ModelCapabilityProfile] = {}   # key = model_id

    @classmethod
    def register(cls, profile: ModelCapabilityProfile) -> None:
        cls._profiles[profile.model_id] = profile

    @classmethod
    def get(cls, model_id: str) -> ModelCapabilityProfile | None:
        return cls._profiles.get(model_id)

    @classmethod
    def all(cls) -> list[ModelCapabilityProfile]:
        return list(cls._profiles.values())

    @classmethod
    def find_capable(cls, **requirements: bool) -> list[ModelCapabilityProfile]:
        """
        Return all profiles where every required capability flag is True.
        E.g. find_capable(sql_generation=True, governance_approved=True)
        """
        result = []
        for p in cls._profiles.values():
            if all(getattr(p, cap, False) == val for cap, val in requirements.items()):
                result.append(p)
        return result

    @classmethod
    def available_count(cls) -> int:
        return len(cls._profiles)


def register_default_profiles() -> None:
    """Register all known model capability profiles. Called at startup."""

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="openai", model_id="gpt-4o", display_name="GPT-4o",
        sql_generation=True, function_calling=True, structured_output=True,
        long_context=True, vision=True, code_generation=True,
        multi_step_reasoning=True, rag_support=True, streaming=True,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.97, sql_score=0.95, accuracy_score=0.97,
        requires_api_key=True, notes="Best overall; use for complex multi-step reasoning",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="openai", model_id="gpt-4o-mini", display_name="GPT-4o Mini",
        sql_generation=True, function_calling=True, structured_output=True,
        long_context=True, code_generation=True,
        multi_step_reasoning=True, rag_support=True, streaming=True,
        context_window=128000, cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
        avg_latency_ms=1200, governance_approved=True,
        reasoning_score=0.82, sql_score=0.80, accuracy_score=0.82,
        requires_api_key=True, notes="Cost-optimized for medium complexity tasks",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="gpt_oss", model_id="openai/gpt-oss-20b", display_name="GPT-OSS 20b",
        sql_generation=True, structured_output=True,
        long_context=True, code_generation=True,
        multi_step_reasoning=True, rag_support=True,
        context_window=131072, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        avg_latency_ms=5000, governance_approved=True,
        reasoning_score=0.78, sql_score=0.75, accuracy_score=0.78,
        requires_api_key=False, local_only=False,
        notes="Open-weight via HF Serverless API; zero per-token cost",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="anthropic", model_id="claude-3-5-sonnet", display_name="Claude 3.5 Sonnet",
        sql_generation=True, function_calling=True, structured_output=True,
        long_context=True, code_generation=True,
        multi_step_reasoning=True, rag_support=True, streaming=True,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.95, sql_score=0.88, accuracy_score=0.95,
        requires_api_key=True, notes="Excellent for long-document analysis (200k context)",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="granite", model_id="granite-13b-chat", display_name="IBM Granite 13b",
        sql_generation=True, structured_output=True,
        long_context=False, code_generation=True,
        multi_step_reasoning=False, rag_support=True,
        context_window=8192, cost_per_1k_input=0.0003, cost_per_1k_output=0.0006,
        avg_latency_ms=2000, governance_approved=True,
        reasoning_score=0.70, sql_score=0.72, accuracy_score=0.71,
        requires_api_key=True,
        notes="IBM enterprise model; ideal for regulated industries",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="gemini", model_id="gemini-1.5-flash", display_name="Gemini 1.5 Flash",
        sql_generation=True, function_calling=True, structured_output=True,
        long_context=True, vision=True, code_generation=True,
        multi_step_reasoning=True, rag_support=True, streaming=True,
        context_window=1000000, cost_per_1k_input=0.00035, cost_per_1k_output=0.00105,
        avg_latency_ms=1500, governance_approved=True,
        reasoning_score=0.85, sql_score=0.82, accuracy_score=0.85,
        requires_api_key=True, notes="Best cost/speed for vision tasks; 1M context",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ollama", model_id="llama3", display_name="Llama 3 (Ollama)",
        sql_generation=True, structured_output=True,
        code_generation=True, rag_support=True,
        context_window=8192, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        avg_latency_ms=8000, governance_approved=True,
        reasoning_score=0.72, sql_score=0.65, accuracy_score=0.72,
        requires_api_key=False, local_only=True,
        notes="Fully local; air-gapped environments; requires local GPU",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="mock", model_id="mock-gpt-demo", display_name="Mock LLM (Demo)",
        sql_generation=True, structured_output=True, rag_support=True,
        context_window=16000, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        avg_latency_ms=120, governance_approved=True,
        reasoning_score=0.0, sql_score=0.0, accuracy_score=0.0,
        requires_api_key=False, local_only=True,
        notes="Deterministic canned responses for testing; no real inference",
    ))
