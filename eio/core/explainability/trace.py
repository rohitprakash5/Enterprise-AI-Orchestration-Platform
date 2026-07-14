"""
Explainability Trace
======================
Every EIO response includes a complete, structured trace of the request execution.
This trace is the primary audit artifact and is surfaced directly in the UI.

The trace captures:
  - Which agents ran and in what order (agent_timeline)
  - Which model was selected and why (routing_decision)
  - What SQL was generated (sql_generated)
  - Which documents were retrieved (documents_retrieved)
  - Which RAG passages were used (rag_passages)
  - Data quality findings (data_quality_report)
  - Data lineage ledger (lineage_entries)
  - Confidence score, token usage, cost, and total latency
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    """A single agent execution step within the trace timeline."""

    agent_name: str
    started_at: datetime
    ended_at: datetime | None = None
    input_summary: str = ""
    output_summary: str = ""
    status: str = "running"   # running | success | error | skipped
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return 0.0


class RAGPassage(BaseModel):
    """A retrieved passage from the vector store."""

    text: str
    source: str
    page: int | None = None
    score: float = 0.0
    chunk_index: int = 0


class LineageEntry(BaseModel):
    """A single data lineage record."""

    source_type: str      # "database" | "document" | "vector_store"
    source_name: str
    operation: str        # "query" | "read" | "embed" | "search"
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataQualityReport(BaseModel):
    """Summary of data quality findings for a query result."""

    total_rows: int = 0
    null_columns: list[str] = Field(default_factory=list)
    zero_value_columns: list[str] = Field(default_factory=list)
    anomaly_flags: list[str] = Field(default_factory=list)
    quality_score: float = 1.0   # 1.0 = clean, 0.0 = highly suspect
    notes: str = ""


class ExplainabilityTrace(BaseModel):
    """
    Complete explainability trace for a single EIO request.
    Serializable to JSON and returned with every API response.
    """

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    user_id: str = ""
    user_query: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None

    # Enhanced agent execution timeline (includes policy/registry/router steps)
    agent_timeline: list[AgentStep] = Field(default_factory=list)

    # AI Decision Engine output (replaces simple routing_decision)
    ai_decision: dict[str, Any] | None = None          # AIDecisionResult as dict
    routing_decision: dict[str, Any] | None = None     # kept for backward-compat

    # ── Planner Dashboard (Doc1 #2 + Doc2 #10) ────────────────────────────────
    planner_intent: str = ""
    planner_skills: list[str] = Field(default_factory=list)
    planner_tools: list[str] = Field(default_factory=list)
    planner_execution_strategy: str = ""

    # Doc2 #1: Query classification
    query_category: str = ""          # database|document|hybrid|metadata|glossary|general|unsupported|insufficient_data

    # Doc2 #2/#3/#8: Feasibility + Gap Analysis + Evidence Availability
    is_feasible: bool = True
    feasibility_reason: str = ""
    required_evidence: list[str] = Field(default_factory=list)
    available_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)

    # Doc2 #5/#6: Recommendations + Connector Suggestions
    recommendations: list[str] = Field(default_factory=list)
    connector_suggestions: list[dict[str, str]] = Field(default_factory=list)
    possible_evidence_locations: list[str] = Field(default_factory=list)

    # Doc2 #10: Planner Reasoning Dashboard
    detected_entities: list[str] = Field(default_factory=list)
    planner_reasoning: str = ""
    estimated_cost_explanation: str = ""

    # Doc2 #11: Enterprise Readiness Score
    readiness_score: float = 1.0          # 0.0–1.0
    readiness_label: str = ""             # "Full Coverage" | "Partial" | "Insufficient"
    skipped_stages: list[dict[str, str]] = Field(default_factory=list)   # [{stage, reason}]

    # Doc2 #12: Data Acquisition Recommendations
    data_acquisition_recs: list[str] = Field(default_factory=list)

    # Doc2 #13: Intelligent Failure Handling
    failure_category: str = ""    # no_data|permission_denied|connector_offline|llm_failure|
                                  # sql_failure|db_timeout|rag_failure|partial_evidence|none

    # Signature: Knowledge Coverage Score
    knowledge_coverage: dict[str, Any] = Field(default_factory=dict)
    # {sources: [{name, available, icon}], overall_pct: 41, recommendation: "..."}

    # ── Multi-Source Fallback ─────────────────────────────────────────────────
    # Populated by the Orchestrator's fallback engine when primary sources are missing
    fallback_state: dict[str, Any] = Field(default_factory=dict)
    # {triggered, primary_source_missing, sources_searched, accumulated_confidence,
    #  requires_user_confirmation, confirmation_message, secondary_sources_used}

    # ── Enterprise Knowledge Advisor ─────────────────────────────────────────
    # Populated after every infeasible or low-confidence query
    knowledge_advisory: dict[str, Any] = Field(default_factory=dict)
    # {blocking_sources, recommendations, advisory_headline, advisory_detail}

    # ── Source Priority List (from Planner) ──────────────────────────────────
    # Ordered list of evidence sources the planner recommends searching
    source_priorities: list[dict[str, Any]] = Field(default_factory=list)
    # [{id, name, priority, weight, doc_patterns, connector}]

    # ── Confidence Improvement Projections (signature feature) ───────────────
    # Shows exactly how much each missing source would improve answer quality
    confidence_projections: list[dict[str, Any]] = Field(default_factory=list)
    # [{source_name, confidence_if_added, delta_pct}]

    # SQL
    sql_generated: str | None = None
    sql_validated: bool = False
    db_connector_type: str = ""
    db_execution_time_ms: float = 0.0
    db_rows_returned: int = 0
    db_cache_hit: bool = False

    # Documents
    documents_retrieved: list[str] = Field(default_factory=list)
    rag_passages: list[RAGPassage] = Field(default_factory=list)
    storage_provider: str = ""
    vector_db: str = "chromadb"
    rag_retrieval_time_ms: float = 0.0

    # Evidence summary
    evidence_sources: list[str] = Field(default_factory=list)

    # Data quality & lineage
    data_quality_report: DataQualityReport | None = None
    lineage_entries: list[LineageEntry] = Field(default_factory=list)

    # Governance
    governance: dict[str, Any] = Field(default_factory=dict)
    user_context: dict[str, Any] = Field(default_factory=dict)

    # Policy
    policy_violations: list[str] = Field(default_factory=list)
    policy_warnings: list[str] = Field(default_factory=list)

    # Observability
    llm_call_count: int = 0
    db_call_count: int = 0
    doc_retrieval_count: int = 0
    agent_count: int = 0
    data_source_count: int = 0

    # Aggregates (computed in finalize())
    confidence_score: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0

    # ── Mutation helpers ──────────────────────────────────────────────────

    def begin_step(self, agent_name: str, input_summary: str = "") -> AgentStep:
        """Start a new agent step and append it to the timeline."""
        step = AgentStep(
            agent_name=agent_name,
            started_at=datetime.utcnow(),
            input_summary=input_summary,
            status="running",
        )
        self.agent_timeline.append(step)
        return step

    def end_step(
        self,
        step: AgentStep,
        output_summary: str = "",
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mark a step as complete."""
        step.ended_at = datetime.utcnow()
        step.output_summary = output_summary
        step.status = status
        step.error = error
        if metadata:
            step.metadata.update(metadata)

    def add_lineage(
        self, source_type: str, source_name: str, operation: str, details: str = ""
    ) -> None:
        self.lineage_entries.append(
            LineageEntry(
                source_type=source_type,
                source_name=source_name,
                operation=operation,
                details=details,
            )
        )

    def finalize(
        self,
        total_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> None:
        """
        Compute aggregate metrics and set ended_at.
        Called by the Orchestrator after the final agent completes.
        """
        self.ended_at = datetime.utcnow()
        self.total_tokens = total_tokens
        self.total_cost_usd = total_cost_usd

        if self.started_at and self.ended_at:
            self.total_latency_ms = (
                (self.ended_at - self.started_at).total_seconds() * 1000
            )

        # ── Doc2 #7: Evidence-based Confidence Engine ─────────────────────
        has_sql_data = self.db_rows_returned > 0
        has_rag_data = len(self.rag_passages) > 0

        evidence_score = (
            len(self.available_evidence) / max(1, len(self.required_evidence))
            if self.required_evidence else (1.0 if (has_sql_data or has_rag_data) else 0.0)
        )
        planner_score = 1.0 if any(
            s.agent_name == "planner" and s.status == "success"
            for s in self.agent_timeline
        ) else 0.0
        metadata_steps = [s for s in self.agent_timeline if s.agent_name == "metadata_discovery"]
        metadata_score = 1.0 if metadata_steps and any(
            s.status == "success" for s in metadata_steps
        ) else (1.0 if not metadata_steps else 0.0)
        coverage_score = (self.knowledge_coverage.get("overall_pct", 0) / 100) if self.knowledge_coverage else 0.0

        confidence = (
            (0.4 * evidence_score) +
            (0.2 * planner_score) +
            (0.2 * metadata_score) +
            (0.2 * coverage_score)
        )

        if self.data_quality_report:
            confidence *= self.data_quality_report.quality_score
        if self.policy_violations:
            confidence *= max(0.0, 1.0 - (len(self.policy_violations) * 0.15))
        if not self.sql_validated and self.sql_generated:
            confidence *= 0.85
        if self.failure_category and self.failure_category not in ("none", ""):
            confidence *= 0.60
        if not self.is_feasible:
            confidence *= 0.25

        self.confidence_score = round(min(1.0, max(0.0, confidence)), 3)
        self.governance["confidence_breakdown"] = {
            "evidence": round(evidence_score, 3),
            "planner": round(planner_score, 3),
            "metadata": round(metadata_score, 3),
            "knowledge_coverage": round(coverage_score, 3),
            "final": self.confidence_score,
        }

        # ── Doc2 #11: Enterprise Readiness Score ──────────────────────────
        if self.required_evidence:
            avail = len(self.available_evidence)
            total_req = len(self.required_evidence)
            self.readiness_score = round(avail / total_req, 2)
        elif has_sql_data or has_rag_data:
            self.readiness_score = 1.0
        elif not has_sql_data and not has_rag_data and self.sql_generated:
            self.readiness_score = 0.4
        else:
            self.readiness_score = 0.0 if is_infeasible else 0.7

        if self.readiness_score >= 0.85:
            self.readiness_label = "Full Coverage"
        elif self.readiness_score >= 0.50:
            self.readiness_label = "Partial Coverage"
        else:
            self.readiness_label = "Insufficient Data"

    def to_summary(self) -> dict[str, Any]:
        """Compact summary dict for logging and display."""
        return {
            "request_id": self.request_id,
            "query": self.user_query[:80],
            "agents_run": [s.agent_name for s in self.agent_timeline],
            "model": self.routing_decision.get("model") if self.routing_decision else None,
            "sql": bool(self.sql_generated),
            "rag_passages": len(self.rag_passages),
            "confidence": self.confidence_score,
            "tokens": self.total_tokens,
            "cost_usd": self.total_cost_usd,
            "latency_ms": round(self.total_latency_ms, 1),
        }
