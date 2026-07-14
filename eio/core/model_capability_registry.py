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

    # ── IBM ICA Agents ──────────────────────────────────────────────────────
    # Each ICA agent is registered using its UUID as the model_id.
    # Capabilities are derived from the agent's meta.capabilities field in
    # the GET /agents/models API response (2025-06-04).

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="d464de5e-01b5-461a-94df-d6d0e34a3cfe",
        display_name="ICA: Internet Researcher",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA agent: real-time web search and research. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="70852bb7-7386-4a54-9e31-2af43183f3dd",
        display_name="ICA: Market Research Agent",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA agent: market trends, SWOT, competitor analysis. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="33cda11d-184b-414e-9050-e12f184e245a",
        display_name="ICA: Analyze Logs & Recommend Solutions (v1)",
        rag_support=True, vision=True, code_generation=True,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.93, sql_score=0.0, accuracy_score=0.93,
        requires_api_key=True,
        notes="ICA agent: log analysis, error detection. Base: claude-sonnet-3-7",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="eb4d7a7e-274f-4036-a61f-1c1b88ba5d23",
        display_name="ICA: Analyze Logs & Recommend Solutions (v2)",
        rag_support=True, vision=True, code_generation=True,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.95, sql_score=0.0, accuracy_score=0.95,
        requires_api_key=True,
        notes="ICA agent: log analysis, error detection. Base: claude-sonnet-4-5",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="02e9b2bd-acd8-4001-b440-38398589ae8a",
        display_name="ICA: PlantUML Diagram Creator",
        rag_support=False, vision=True, code_generation=True,
        multi_step_reasoning=False, streaming=False,
        context_window=128000, cost_per_1k_input=0.00027, cost_per_1k_output=0.00085,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.78, sql_score=0.0, accuracy_score=0.78,
        requires_api_key=True,
        notes="ICA agent: PlantUML diagrams. Base: meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="92ab6124-60cd-42a6-9d62-d7ea413f2b6e",
        display_name="ICA: Process Flow Diagram Agent",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.85, sql_score=0.0, accuracy_score=0.85,
        requires_api_key=True,
        notes="ICA agent: process flow and architecture diagrams. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="d6b2274e-4c40-415b-912b-9bdc915b0b46",
        display_name="ICA: Draw.IO Agent",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.95, sql_score=0.0, accuracy_score=0.95,
        requires_api_key=True,
        notes="ICA agent: interactive Draw.IO diagrams. Base: claude-sonnet-4-6",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="fb668f5d-f521-4222-8f4f-b3322be6bd43",
        display_name="ICA: Image Generator",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=False, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=5000, governance_approved=True,
        reasoning_score=0.80, sql_score=0.0, accuracy_score=0.80,
        requires_api_key=True,
        notes="ICA agent: image generation. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="b7702938-10ed-45a6-972d-53720a9121e2",
        display_name="ICA: Image Generator 2.0",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=False, streaming=False,
        context_window=1000000, cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.85, sql_score=0.0, accuracy_score=0.85,
        requires_api_key=True,
        notes="ICA agent: image generation. Base: gemini-2.5-flash",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="5be26b56-1690-46cf-b278-1f35b5938a7a",
        display_name="ICA: Chart Creation Agent",
        rag_support=False, vision=True, code_generation=True,
        multi_step_reasoning=False, streaming=False,
        context_window=1000000, cost_per_1k_input=0.0035, cost_per_1k_output=0.0105,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.87, sql_score=0.0, accuracy_score=0.87,
        requires_api_key=True,
        notes="ICA agent: bar/pie/line/histogram charts. Base: gemini-3.1-pro-preview",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="1bf8d13e-d252-485a-a5dd-8bfba9c60a92",
        display_name="ICA: Agent Translate",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=False, streaming=False,
        context_window=32768, cost_per_1k_input=0.0002, cost_per_1k_output=0.0004,
        avg_latency_ms=1500, governance_approved=True,
        reasoning_score=0.72, sql_score=0.0, accuracy_score=0.72,
        requires_api_key=True,
        notes="ICA agent: multilingual translation. Base: ibm/granite-4-h-small",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="09398556-663a-447a-9c68-603fdaa7b83f",
        display_name="ICA: Language Translator Agent",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=False, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=2000, governance_approved=True,
        reasoning_score=0.85, sql_score=0.0, accuracy_score=0.85,
        requires_api_key=True,
        notes="ICA agent: culturally-sensitive translation. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="e7890fb8-d38b-4b1a-a068-5bf195cb37ac",
        display_name="ICA: BASISAssistant",
        rag_support=True, vision=True, code_generation=True,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.93, sql_score=0.0, accuracy_score=0.93,
        requires_api_key=True,
        notes="ICA agent: SAP BASIS expert (transaction codes, HANA). Base: claude-sonnet-3-7",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="1b473159-4357-4300-beea-420fcd2e95bf",
        display_name="ICA: Excel Builder",
        rag_support=True, vision=True, code_generation=True,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.60, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA agent: Excel formulas, pivot tables, VBA. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="4a387cdb-0c48-45c4-952c-103f7e78d819",
        display_name="ICA: Blog Creator",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.00027, cost_per_1k_output=0.00085,
        avg_latency_ms=3500, governance_approved=True,
        reasoning_score=0.78, sql_score=0.0, accuracy_score=0.78,
        requires_api_key=True,
        notes="ICA agent: SEO blog writing. Base: meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="8a9c8368-8057-4c76-8e83-11c9dff8c1f7",
        display_name="ICA: Generate User Persona",
        rag_support=False, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=32768, cost_per_1k_input=0.0002, cost_per_1k_output=0.0004,
        avg_latency_ms=2000, governance_approved=True,
        reasoning_score=0.72, sql_score=0.0, accuracy_score=0.72,
        requires_api_key=True,
        notes="ICA agent: UX persona generation. Base: ibm/granite-4-h-small",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="33980371-b340-4b45-8def-1298054c718d",
        display_name="ICA: Internet Fact Checker",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.00027, cost_per_1k_output=0.00085,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.80, sql_score=0.0, accuracy_score=0.80,
        requires_api_key=True,
        notes="ICA agent: fact verification with web search. Base: meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="d7ac3864-09a7-4fe1-9828-0904e4ef9f58",
        display_name="ICA: Prompt Generator",
        rag_support=False, vision=True, code_generation=True,
        multi_step_reasoning=True, streaming=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA agent: AI prompt engineering. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="241f8e4f-9b3e-45cb-ac99-713de8d26bf3",
        display_name="ICA: Deck, Doc & Excel Generator",
        rag_support=True, vision=True, code_generation=True,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=5000, governance_approved=True,
        reasoning_score=0.95, sql_score=0.0, accuracy_score=0.95,
        requires_api_key=True,
        notes="ICA agent: executive decks, Word docs, Excel models. Base: claude-sonnet-4-5",
    ))

    # SDLC / Agile agents
    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="c0a9a0e2-6224-4a31-87b9-55f495525b74",
        display_name="ICA: Generate User Stories",
        structured_output=True, code_generation=False,
        multi_step_reasoning=True, rag_support=True,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA SDLC agent: Agile user story generation. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="8970a835-0324-4305-8133-c5046f32b46d",
        display_name="ICA: Generate Test Cases",
        structured_output=True, code_generation=True,
        multi_step_reasoning=True, rag_support=True,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA SDLC agent: enterprise test case generation. Base: gpt-5.1-chat-gus",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="59354143-dd30-4f27-95d7-a4f800b6b8ef",
        display_name="ICA: Estimate User Story Complexity",
        structured_output=True, code_generation=False,
        multi_step_reasoning=True, rag_support=False,
        context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        avg_latency_ms=3000, governance_approved=True,
        reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
        requires_api_key=True,
        notes="ICA SDLC agent: story point estimation. Base: gpt-5.1-chat-gus",
    ))

    # AI Governance agents
    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="a9bb5fb0-9564-4715-9166-9065da375766",
        display_name="ICA: AI Governance A02 — Strategic Alignment",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.95, sql_score=0.0, accuracy_score=0.95,
        requires_api_key=True,
        notes="ICA agent: IBM AI Governance workshop facilitation. Base: claude-sonnet-4-5",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="322c1369-81b3-460b-bd6a-af06f49a0d1a",
        display_name="ICA: AI Governance A01 — Backstory Generation",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.95, sql_score=0.0, accuracy_score=0.95,
        requires_api_key=True,
        notes="ICA agent: AI Governance scenario creation. Base: claude-sonnet-4-5",
    ))

    ModelCapabilityRegistry.register(ModelCapabilityProfile(
        provider="ica", model_id="eaa58f34-80c5-4d32-bc87-45f15ccbc6bc",
        display_name="ICA: AI Governance A05 — Layers of Effect",
        rag_support=True, vision=True, code_generation=False,
        multi_step_reasoning=True, streaming=False,
        context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        avg_latency_ms=4000, governance_approved=True,
        reasoning_score=0.95, sql_score=0.0, accuracy_score=0.95,
        requires_api_key=True,
        notes="ICA agent: Design Thinking / AI Governance facilitation. Base: claude-sonnet-4-5",
    ))

    # FT (Finance/Transformation) suite
    for _uid, _name in [
        ("91824904-2c7b-40a2-8935-a2c382ca83b1", "ICA: FT Sustainability Pain Point Generator"),
        ("3cf5e811-ea7c-4041-b749-0a5052f43947", "ICA: FT Controls Initiative Recommendations Generator"),
        ("10231cb4-f7e9-429c-8352-81b18b0dcf26", "ICA: FT Supply Chain Finance Initiative Recommendations Generator"),
        ("5a78225a-124a-4b0f-81ba-75be6da79282", "ICA: FT Controls Pain Point Generator"),
        ("460fe658-0d54-45c4-b4fd-dbb5545c29b5", "ICA: FT Sustainability Disclosure Assistant"),
        ("2e594baf-65a2-4c64-a030-968ef710232d", "ICA: FT Sustainability Initiative Recommendations Generator"),
        ("c94d1efa-0e3c-4126-871c-1e49de37d5c7", "ICA: FT Supply Chain Finance Pain Point Generator"),
    ]:
        ModelCapabilityRegistry.register(ModelCapabilityProfile(
            provider="ica", model_id=_uid, display_name=_name,
            rag_support=True, vision=True, code_generation=False,
            multi_step_reasoning=True, streaming=False,
            context_window=200000, cost_per_1k_input=0.003, cost_per_1k_output=0.015,
            avg_latency_ms=4000, governance_approved=True,
            reasoning_score=0.93, sql_score=0.0, accuracy_score=0.93,
            requires_api_key=True,
            notes="ICA FT suite agent. Base: claude-sonnet-4-5",
        ))

    # UX / SDLC remaining agents
    for _uid, _name in [
        ("790b01dc-c053-470a-9b08-c50bdbf7cb76", "ICA: Generate Interview Questionnaire"),
        ("7f156b76-4c67-4cb1-bc3a-f407bd513f42", "ICA: Extract Pain Points from User Research"),
        ("7a54bfa5-bc43-439e-ba72-c463a3510d00", "ICA: Generate Manual Test Cases from Requirements"),
        ("be80526a-ebc3-4046-8fea-0025c6c1e415", "ICA: Generate Manual Test Cases from User Story"),
        ("027c17e7-5405-4bd4-b7d8-c4c39359ab6a", "ICA: Generate Golden Thread"),
    ]:
        ModelCapabilityRegistry.register(ModelCapabilityProfile(
            provider="ica", model_id=_uid, display_name=_name,
            structured_output=True, rag_support=True, vision=True,
            multi_step_reasoning=True, streaming=False,
            context_window=128000, cost_per_1k_input=0.005, cost_per_1k_output=0.015,
            avg_latency_ms=3000, governance_approved=True,
            reasoning_score=0.88, sql_score=0.0, accuracy_score=0.88,
            requires_api_key=True,
            notes="ICA SDLC/UX agent. Base: gpt-5.1-chat-gus",
        ))


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
