"""
Query Route
============
POST /api/v1/query — Execute a business query through the EIO orchestrator.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from eio.api.schemas import (
    AgentStepDTO,
    ConfidenceProjectionDTO,
    DataQualityDTO,
    DataResultDTO,
    ExplainabilityDTO,
    FallbackStateDTO,
    KnowledgeAdvisoryDTO,
    LineageEntryDTO,
    QueryRequest,
    QueryResponse,
    RAGPassageDTO,
    RoutingDecisionDTO,
    SourceGapRecommendationDTO,
    SourceSearchResultDTO,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Query"])


@router.post("/query", response_model=QueryResponse)
async def run_query(request: Request, body: QueryRequest) -> QueryResponse:
    """
    Execute a natural language business query through the EIO multi-agent pipeline.
    Returns the answer, structured data results, RAG passages, and a full explainability trace.
    """
    orchestrator = request.app.state.orchestrator

    try:
        context = orchestrator.run(
            user_query=body.user_query,
            user_id=body.user_id,
            session_id=body.session_id,
            user_confirmed=body.user_confirmed,
        )
    except Exception as exc:
        logger.error(f"Orchestrator error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {exc}")

    trace = context.trace

    # ── Build agent timeline ─────────────────────────────────────────────
    timeline = [
        AgentStepDTO(
            agent_name=step.agent_name,
            duration_ms=round(step.duration_ms, 1),
            status=step.status,
            input_summary=step.input_summary,
            output_summary=step.output_summary,
            error=step.error,
        )
        for step in trace.agent_timeline
    ]

    # ── Routing decision ─────────────────────────────────────────────────
    routing_dto = None
    if trace.routing_decision:
        rd = trace.routing_decision
        routing_dto = RoutingDecisionDTO(
            provider=rd.get("provider", ""),
            model=rd.get("model", ""),
            reason=rd.get("reason", ""),
            estimated_cost_usd=rd.get("estimated_cost_usd", 0.0),
            complexity=rd.get("complexity", ""),
            policy_applied=rd.get("policy_applied", []),
        )

    # ── RAG passages ─────────────────────────────────────────────────────
    rag_dtos = [
        RAGPassageDTO(
            text=p.text[:800],
            source=p.source,
            page=p.page,
            score=p.score,
        )
        for p in trace.rag_passages
    ]

    # ── Data quality ──────────────────────────────────────────────────────
    dq_dto = None
    if trace.data_quality_report:
        dq = trace.data_quality_report
        dq_dto = DataQualityDTO(
            total_rows=dq.total_rows,
            null_columns=dq.null_columns,
            anomaly_flags=dq.anomaly_flags,
            quality_score=dq.quality_score,
            notes=dq.notes,
        )

    # ── Lineage ───────────────────────────────────────────────────────────
    lineage_dtos = [
        LineageEntryDTO(
            source_type=e.source_type,
            source_name=e.source_name,
            operation=e.operation,
            details=e.details,
            timestamp=e.timestamp.isoformat(),
        )
        for e in trace.lineage_entries
    ]

    # ── SQL results ────────────────────────────────────────────────────────
    data_result_dto = None
    if context.sql_result and context.sql_result.success:
        data_result_dto = DataResultDTO(
            columns=context.sql_result.columns,
            rows=context.sql_result.rows,
            row_count=context.sql_result.row_count,
            execution_time_ms=context.sql_result.execution_time_ms,
        )

    explainability = ExplainabilityDTO(
        # Core
        request_id=trace.request_id,
        agent_timeline=timeline,
        routing_decision=routing_dto,

        # AI Decision Engine (Enhancement #1 / #3 / #4 / #5 / #6)
        ai_decision=trace.ai_decision,

        # SQL
        sql_generated=trace.sql_generated,
        sql_validated=trace.sql_validated,

        # DB execution details (Enhancement #8)
        db_connector_type=trace.db_connector_type,
        db_execution_time_ms=trace.db_execution_time_ms,
        db_rows_returned=trace.db_rows_returned,
        db_cache_hit=trace.db_cache_hit,

        # Document retrieval (Enhancement #9)
        documents_retrieved=trace.documents_retrieved,
        rag_passages=rag_dtos,
        storage_provider=trace.storage_provider,
        vector_db=trace.vector_db,
        rag_retrieval_time_ms=trace.rag_retrieval_time_ms,

        # Evidence sources (Enhancement #10)
        evidence_sources=trace.evidence_sources,

        # Data quality & lineage
        data_quality=dq_dto,
        lineage=lineage_dtos,

        # Governance dashboard (Enhancement #11 / #12)
        governance=trace.governance,
        user_context=trace.user_context,

        # Policy
        policy_violations=trace.policy_violations,
        policy_warnings=trace.policy_warnings,

        # Planner dashboard (Enhancement #2 + Doc2 all)
        planner_intent=trace.planner_intent,
        planner_skills=trace.planner_skills,
        planner_tools=trace.planner_tools,
        planner_execution_strategy=trace.planner_execution_strategy,

        # Doc2: Intelligent Planning fields
        query_category=trace.query_category,
        is_feasible=trace.is_feasible,
        feasibility_reason=trace.feasibility_reason,
        detected_entities=trace.detected_entities,
        required_evidence=trace.required_evidence,
        available_evidence=trace.available_evidence,
        missing_evidence=trace.missing_evidence,
        recommendations=trace.recommendations,
        connector_suggestions=trace.connector_suggestions,
        possible_evidence_locations=trace.possible_evidence_locations,
        planner_reasoning=trace.planner_reasoning,
        estimated_cost_explanation=trace.estimated_cost_explanation,
        readiness_score=trace.readiness_score,
        readiness_label=trace.readiness_label,
        skipped_stages=trace.skipped_stages,
        data_acquisition_recs=trace.data_acquisition_recs,
        failure_category=trace.failure_category,
        knowledge_coverage=trace.knowledge_coverage,

        # Multi-source fallback (new)
        fallback_state=FallbackStateDTO(**trace.fallback_state) if trace.fallback_state else None,

        # Knowledge Advisor (new)
        knowledge_advisory=KnowledgeAdvisoryDTO(
            query=trace.knowledge_advisory.get("query", ""),
            current_confidence_pct=trace.knowledge_advisory.get("current_confidence_pct", 0),
            blocking_sources=trace.knowledge_advisory.get("blocking_sources", []),
            advisory_headline=trace.knowledge_advisory.get("advisory_headline", ""),
            advisory_detail=trace.knowledge_advisory.get("advisory_detail", ""),
            recommendations=[
                SourceGapRecommendationDTO(**r)
                for r in trace.knowledge_advisory.get("recommendations", [])
            ],
            confidence_projections=[
                ConfidenceProjectionDTO(**p)
                for p in trace.knowledge_advisory.get("confidence_projections", [])
            ],
        ) if trace.knowledge_advisory else None,

        # Source priorities + confidence projections (new)
        source_priorities=trace.source_priorities,
        confidence_projections=[
            ConfidenceProjectionDTO(**p) for p in trace.confidence_projections
        ],

        # Observability counters (Enhancement #14)
        llm_call_count=trace.llm_call_count,
        db_call_count=trace.db_call_count,
        doc_retrieval_count=trace.doc_retrieval_count,
        agent_count=trace.agent_count,
        data_source_count=trace.data_source_count,

        # Aggregates
        confidence_score=trace.confidence_score,
        total_tokens=trace.total_tokens,
        total_cost_usd=trace.total_cost_usd,
        total_latency_ms=round(trace.total_latency_ms, 1),
    )

    return QueryResponse(
        request_id=trace.request_id,
        answer=context.final_answer,
        sql_query=trace.sql_generated,
        data_results=data_result_dto,
        rag_passages=rag_dtos,
        explainability=explainability,
        policy_violations=trace.policy_violations,
        policy_warnings=trace.policy_warnings,
        confidence_score=trace.confidence_score,
        total_tokens=trace.total_tokens,
        total_cost_usd=trace.total_cost_usd,
        total_latency_ms=round(trace.total_latency_ms, 1),
    )
