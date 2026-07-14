"""
EIO API Schemas
================
Pydantic models for all API request/response contracts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    user_query: str = Field(..., min_length=1, max_length=4000)
    user_id: str = Field(default="anonymous")
    session_id: str = Field(default="")
    user_confirmed: bool = Field(
        default=False,
        description="Set true to proceed with a best-effort answer after a multi-source fallback confirmation prompt",
    )


class AgentStepDTO(BaseModel):
    agent_name: str
    duration_ms: float
    status: str
    input_summary: str
    output_summary: str
    error: str | None = None


class RoutingDecisionDTO(BaseModel):
    provider: str
    model: str
    reason: str
    estimated_cost_usd: float
    complexity: str
    policy_applied: list[str]


class RAGPassageDTO(BaseModel):
    text: str
    source: str
    page: int | None
    score: float


class DataQualityDTO(BaseModel):
    total_rows: int
    null_columns: list[str]
    anomaly_flags: list[str]
    quality_score: float
    notes: str


class LineageEntryDTO(BaseModel):
    source_type: str
    source_name: str
    operation: str
    details: str
    timestamp: str


class SourceSearchResultDTO(BaseModel):
    """One step in the multi-source fallback cascade."""
    source_id:               str
    source_name:             str
    priority:                int
    found:                   bool
    confidence_contribution: float = 0.0
    details:                 str = ""


class FallbackStateDTO(BaseModel):
    """Complete state of the multi-source fallback process."""
    triggered:                  bool = False
    primary_source_missing:     str = ""
    sources_searched:           list[SourceSearchResultDTO] = Field(default_factory=list)
    accumulated_confidence:     float = 0.0
    requires_user_confirmation: bool = False
    user_confirmed:             bool = False
    best_effort_answer:         bool = False
    confirmation_message:       str = ""
    secondary_sources_used:     list[str] = Field(default_factory=list)


class SourceGapRecommendationDTO(BaseModel):
    """One actionable recommendation from the Enterprise Knowledge Advisor."""
    source_id:           str
    source_name:         str
    connection_action:   str
    priority:            str
    business_impact:     str
    coverage_gain_pct:   int
    confidence_gain_pct: int
    effort:              str
    why_missing:         str = ""


class ConfidenceProjectionDTO(BaseModel):
    """How confidence changes as each missing source is added."""
    source_name:          str
    confidence_if_added:  int
    delta_pct:            int


class KnowledgeAdvisoryDTO(BaseModel):
    """Enterprise Knowledge Advisor output — shown on every failed/partial query."""
    query:                   str = ""
    current_confidence_pct:  int = 0
    blocking_sources:        list[str] = Field(default_factory=list)
    advisory_headline:       str = ""
    advisory_detail:         str = ""
    recommendations:         list[SourceGapRecommendationDTO] = Field(default_factory=list)
    confidence_projections:  list[ConfidenceProjectionDTO] = Field(default_factory=list)


class ExplainabilityDTO(BaseModel):
    request_id: str
    agent_timeline: list[AgentStepDTO]
    routing_decision: RoutingDecisionDTO | None
    ai_decision: dict[str, Any] | None = None
    sql_generated: str | None
    sql_validated: bool
    db_connector_type: str = ""
    db_execution_time_ms: float = 0.0
    db_rows_returned: int = 0
    db_cache_hit: bool = False
    documents_retrieved: list[str]
    rag_passages: list[RAGPassageDTO]
    storage_provider: str = ""
    vector_db: str = "chromadb"
    rag_retrieval_time_ms: float = 0.0
    evidence_sources: list[str] = Field(default_factory=list)
    data_quality: DataQualityDTO | None
    lineage: list[LineageEntryDTO]
    governance: dict[str, Any] = Field(default_factory=dict)
    user_context: dict[str, Any] = Field(default_factory=dict)
    policy_violations: list[str]
    policy_warnings: list[str]
    planner_intent: str = ""
    planner_skills: list[str] = Field(default_factory=list)
    planner_tools: list[str] = Field(default_factory=list)
    planner_execution_strategy: str = ""
    # Doc2 fields
    query_category: str = ""
    is_feasible: bool = True
    feasibility_reason: str = ""
    detected_entities: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    available_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    connector_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    possible_evidence_locations: list[str] = Field(default_factory=list)
    planner_reasoning: str = ""
    estimated_cost_explanation: str = ""
    readiness_score: float = 1.0
    readiness_label: str = ""
    skipped_stages: list[dict[str, str]] = Field(default_factory=list)
    data_acquisition_recs: list[str] = Field(default_factory=list)
    failure_category: str = ""
    knowledge_coverage: dict[str, Any] = Field(default_factory=dict)
    # Multi-source fallback + Knowledge Advisor (new)
    fallback_state: FallbackStateDTO | None = None
    knowledge_advisory: KnowledgeAdvisoryDTO | None = None
    source_priorities: list[dict[str, Any]] = Field(default_factory=list)
    confidence_projections: list[ConfidenceProjectionDTO] = Field(default_factory=list)
    llm_call_count: int = 0
    db_call_count: int = 0
    doc_retrieval_count: int = 0
    agent_count: int = 0
    data_source_count: int = 0
    confidence_score: float
    total_tokens: int
    total_cost_usd: float
    total_latency_ms: float


class DataResultDTO(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    execution_time_ms: float


class QueryResponse(BaseModel):
    request_id: str
    answer: str
    sql_query: str | None = None
    data_results: DataResultDTO | None = None
    rag_passages: list[RAGPassageDTO] = Field(default_factory=list)
    explainability: ExplainabilityDTO
    policy_violations: list[str] = Field(default_factory=list)
    policy_warnings: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
