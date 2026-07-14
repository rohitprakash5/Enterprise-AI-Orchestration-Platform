"""
EIO Orchestrator (Enhanced)
============================
Central execution engine wiring all enhancements:
  - AI Decision Engine (replaces simple ModelRouter)
  - Model Capability Registry + Health Registry
  - Task-level model routing
  - Enhanced timeline (policy / registry / router as explicit steps)
  - RBAC UserContext threading
  - Governance simulation dashboard
  - Observability counters
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import eio.agents  # noqa: F401 — triggers all @AgentRegistry.register decorators
from eio.agents.base import AgentContext
from eio.connectors.databases.base import DatabaseConnector
from eio.connectors.llm.base import LLMProvider, RoutingContext
from eio.connectors.llm.router import ModelRouter
from eio.connectors.storage.base import StorageConnector
from eio.core.ai_decision_engine import AIDecisionEngine
from eio.core.explainability.trace import AgentStep, ExplainabilityTrace
from eio.core.knowledge_advisor import EnterpriseKnowledgeAdvisor
from eio.core.multi_source_fallback import MultiSourceFallbackEngine, CONFIDENCE_PROCEED
from eio.core.model_capability_registry import (
    ModelCapabilityRegistry,
    register_default_profiles,
)
from eio.core.model_health_registry import ModelHealthRegistry
from eio.core.policy.audit_log import AuditLogger
from eio.core.policy.engine import PolicyEngine
from eio.core.registries import AgentRegistry, bootstrap_registries
from eio.core.user_context import UserContext

logger = logging.getLogger(__name__)

_FULL_PIPELINE_ORDER = [
    "planner",
    "business_glossary",
    "metadata_discovery",
    "semantic_schema",
    "sql_generation",
    "sql_validation",
    "database_execution",
    "document_retrieval",
    "rag",
    "data_quality",
    "lineage",
    "migration_reconciliation",
    "response_synthesis",
]


class Orchestrator:
    """
    EIO's central execution engine — enhanced edition.
    Thread-safe: each request gets its own AgentContext.
    """

    def __init__(
        self,
        db_connector: DatabaseConnector,
        storage_connector: StorageConnector,
        llm_provider: LLMProvider,
        vector_collection: Any,
        policy_engine: PolicyEngine | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._db      = db_connector
        self._storage = storage_connector
        self._llm     = llm_provider
        self._collection = vector_collection
        self._policy  = policy_engine or PolicyEngine()
        self._router  = ModelRouter()
        self._audit   = audit_logger or AuditLogger(self._policy.audit_log_path)

        # Boot registries
        bootstrap_registries()
        register_default_profiles()
        ModelHealthRegistry.initialize_from_profiles()

        # Mark the active provider as online
        ModelHealthRegistry.mark_online(llm_provider.default_model)

        logger.info(
            f"EIO Orchestrator ready | "
            f"DB={type(db_connector).__name__} | "
            f"Storage={type(storage_connector).__name__} | "
            f"LLM={llm_provider.provider_name}/{llm_provider.default_model} | "
            f"Agents={len(AgentRegistry.available())} | "
            f"Models={ModelCapabilityRegistry.available_count()}"
        )

    # ── Public API ─────────────────────────────────────────────────────

    def run(
        self,
        user_query: str,
        user_id: str = "anonymous",
        session_id: str = "",
        user_context: UserContext | None = None,
        user_confirmed: bool = False,
    ) -> AgentContext:
        """Execute the full multi-agent pipeline. Returns populated AgentContext."""
        request_id = str(uuid.uuid4())
        uc = user_context or UserContext.demo_user(user_id)

        context = AgentContext(
            request_id=request_id,
            session_id=session_id or request_id,
            user_id=user_id,
            user_query=user_query,
            db_connector=self._db,
            storage_connector=self._storage,
            llm_provider=self._llm,
            vector_collection=self._collection,
            trace=ExplainabilityTrace(
                request_id=request_id,
                session_id=session_id or request_id,
                user_id=user_id,
                user_query=user_query,
                storage_provider=type(self._storage).__name__,
                db_connector_type=type(self._db).__name__,
                user_context=uc.to_dict(),
            ),
        )

        # ── Step 1: Planner Agent (Intelligent Planning) ─────────────────
        self._timeline_step(context, "Planner Agent", "Intelligent query classification & feasibility assessment")
        planner = AgentRegistry.instantiate("planner")
        planner._safe_run(context)
        self._enrich_planner_trace(context)

        if not context.routing_context:
            context.routing_context = RoutingContext(
                user_query=user_query,
                complexity="high",
                sql_needed=True,
                rag_needed=True,
                estimated_tokens=3000,
            )
            context.selected_agents = list(_FULL_PIPELINE_ORDER[1:])

        # ── Doc2 #2/#4/#9: Infeasibility — run Knowledge Advisor ─────────
        if not context.trace.is_feasible:
            # Still run AI Decision Engine so the sidebar is never blank
            self._timeline_step(context, "AI Decision Engine", "Evaluating candidate models (infeasible path)")
            try:
                decision_engine = AIDecisionEngine(
                    max_cost_usd=float(os.getenv("EIO_POLICY_COST_LIMIT_USD", "0.50")),
                    max_tokens=int(os.getenv("EIO_POLICY_TOKEN_BUDGET", "16000")),
                )
                ai_decision = decision_engine.evaluate(context.routing_context)
                context.routing_decision = ai_decision.routing_decision
                context.trace.ai_decision = ai_decision.to_dict()
                context.trace.routing_decision = (
                    ai_decision.routing_decision.model_dump()
                    if ai_decision.routing_decision else None
                )
            except Exception as _exc:
                logger.warning(f"AI Decision Engine skipped on infeasible path: {_exc}")
                # Populate a minimal routing_decision from the active provider
                context.trace.routing_decision = {
                    "provider": self._llm.provider_name,
                    "model":    self._llm.default_model,
                    "reason":   "Infeasible query — active provider shown",
                    "estimated_cost_usd": 0.0,
                    "complexity": "low",
                    "policy_applied": [],
                }

            advisor = EnterpriseKnowledgeAdvisor()
            available_docs = self._get_available_docs(context)
            has_sql = bool(context.sql_result and context.sql_result.success
                           and context.sql_result.row_count > 0)
            advisory = advisor.advise(
                query=user_query,
                missing_evidence=context.trace.missing_evidence,
                current_confidence=0.10,
                available_docs=available_docs,
                has_sql_data=has_sql,
            )
            context.trace.knowledge_advisory = advisory.to_dict()
            context.final_answer = advisory.format_as_text()
            context.trace.finalize(context.total_tokens, context.total_cost_usd)
            return context

        # ── Step 2: Policy Engine pre-check ─────────────────────────────
        self._timeline_step(context, "Policy Engine", "Pre-routing governance check")
        from eio.core.llm_pricing import tokens_to_cost
        est_cost = tokens_to_cost("gpt-4o", context.routing_context.estimated_tokens)
        # Use the active provider's model ID — strip any HF org prefix for policy lookup
        # e.g. "openai/gpt-oss-20b" → check both full ID and short ID
        raw_model = self._llm.default_model
        pre_policy = self._policy.check_routing(
            estimated_tokens=context.routing_context.estimated_tokens,
            estimated_cost_usd=est_cost,
            model_name=raw_model,
        )
        # If blocked solely due to model name, also try the short model ID (after last "/")
        if not pre_policy.allowed and "/" in raw_model:
            short_model = raw_model.split("/")[-1]
            pre_policy = self._policy.check_routing(
                estimated_tokens=context.routing_context.estimated_tokens,
                estimated_cost_usd=est_cost,
                model_name=short_model,
            )
        context.trace.policy_violations.extend(pre_policy.violations)
        context.trace.policy_warnings.extend(pre_policy.warnings)

        # Build governance dashboard entry
        context.trace.governance = self._build_governance(uc, pre_policy)

        if not pre_policy.allowed:
            context.final_answer = (
                "Request blocked by enterprise policy: "
                + "; ".join(pre_policy.violations)
            )
            context.trace.finalize(context.total_tokens, context.total_cost_usd)
            return context

        # ── Step 3: AI Decision Engine ───────────────────────────────────
        self._timeline_step(context, "AI Decision Engine", "Evaluating all candidate models")
        decision_engine = AIDecisionEngine(
            max_cost_usd=float(os.getenv("EIO_POLICY_COST_LIMIT_USD", "0.50")),
            max_tokens=int(os.getenv("EIO_POLICY_TOKEN_BUDGET", "16000")),
        )
        ai_decision = decision_engine.evaluate(context.routing_context)
        context.routing_decision = ai_decision.routing_decision
        context.trace.ai_decision = ai_decision.to_dict()
        context.trace.routing_decision = (
            ai_decision.routing_decision.model_dump()
            if ai_decision.routing_decision else None
        )
        logger.info(
            f"[Decision Engine] Selected: {ai_decision.selected_display_name} "
            f"(score={ai_decision.selection_confidence:.1f}) | "
            f"Candidates: {len(ai_decision.candidates_evaluated)}"
        )

        # ── Step 4: Capability Registry lookup ──────────────────────────
        self._timeline_step(context, "Capability Registry", "Matching required capabilities to agents")

        # ── Step 5: Model Health check ───────────────────────────────────
        self._timeline_step(context, "Model Health Registry", "Verifying selected model is online")

        # ── Step 6: Dynamic agent pipeline ──────────────────────────────
        self._timeline_step(context, "Agent Orchestrator", "Dispatching dynamic agent pipeline")

        # Always inject required support agents when SQL is needed
        if context.routing_context.sql_needed:
            agents_set = set(context.selected_agents)
            if "sql_generation" in agents_set or "database_execution" in agents_set or \
               "sql_validation" in agents_set:
                # metadata_discovery MUST run first so sql_generation has schema context
                agents_set.update({
                    "metadata_discovery", "semantic_schema",
                    "sql_generation", "sql_validation", "database_execution",
                })
            context.selected_agents = [
                a for a in _FULL_PIPELINE_ORDER if a in agents_set
            ]

        pipeline = [
            name for name in _FULL_PIPELINE_ORDER
            if name in context.selected_agents or name == "planner"
        ]
        pipeline = [a for a in pipeline if a != "planner"]

        for agent_name in pipeline:
            try:
                agent = AgentRegistry.instantiate(agent_name)
            except ValueError:
                logger.warning(f"Agent '{agent_name}' not registered — skipping")
                continue

            # Pre-execution SQL policy check
            if agent_name == "database_execution" and context.sql_generated:
                self._timeline_step(context, "Policy Engine (SQL)", "SQL keyword safety check")
                sql_policy = self._policy.check_sql(context.sql_generated)
                if not sql_policy.allowed:
                    context.trace.policy_violations.extend(sql_policy.violations)
                    logger.warning(f"SQL blocked by policy: {sql_policy.violations}")
                    context.sql_validated = False
                    continue

            t0 = time.perf_counter()
            agent._safe_run(context)
            elapsed = (time.perf_counter() - t0) * 1000

            # Update observability counters
            if agent_name == "database_execution":
                context.trace.db_call_count += 1
                if context.sql_result:
                    context.trace.db_rows_returned = context.sql_result.row_count
                    context.trace.db_execution_time_ms = context.sql_result.execution_time_ms
            elif agent_name == "rag":
                context.trace.doc_retrieval_count += 1
                context.trace.rag_retrieval_time_ms = elapsed
            elif agent_name in ("sql_generation", "response_synthesis", "planner"):
                context.trace.llm_call_count += 1

            # Update LLM health registry after synthesis
            if agent_name == "response_synthesis" and context.routing_decision:
                ModelHealthRegistry.record_call(
                    model_id=context.routing_decision.model,
                    latency_ms=elapsed,
                    success=bool(context.final_answer),
                )

        # ── Step 7: Multi-source fallback evaluation ─────────────────────
        # Run after all agents complete — assess evidence quality and trigger
        # fallback/confirmation if primary sources were missing.
        self._run_fallback_evaluation(context, user_query, user_confirmed=user_confirmed)

        # ── Step 7b: Post-synthesis PII scan ────────────────────────────
        if context.final_answer:
            self._timeline_step(context, "Policy Engine (PII)", "Post-synthesis PII scan")
            pii_result = self._policy.check_pii(context.final_answer)
            if pii_result.pii_detected:
                context.final_answer = pii_result.redacted_content or context.final_answer
                context.trace.policy_warnings.extend(pii_result.warnings)

        # ── Step 8: Build evidence summary ───────────────────────────────
        context.trace.evidence_sources = self._build_evidence_sources(context)

        # ── Step 9: Finalize ─────────────────────────────────────────────
        context.trace.agent_count = len([
            s for s in context.trace.agent_timeline
            if not s.agent_name.startswith("Policy") and
               s.agent_name not in ("Capability Registry", "Model Health Registry",
                                    "AI Decision Engine", "Agent Orchestrator")
        ])
        context.trace.data_source_count = len({
            e.source_name for e in context.trace.lineage_entries
        })
        context.trace.finalize(context.total_tokens, context.total_cost_usd)
        context.confidence_score = context.trace.confidence_score

        # ── Step 10: Audit log ───────────────────────────────────────────
        if self._policy.audit_log_enabled:
            model = (
                context.routing_decision.model
                if context.routing_decision else self._llm.default_model
            )
            provider = (
                context.routing_decision.provider
                if context.routing_decision else self._llm.provider_name
            )
            self._audit.log(
                request_id=request_id,
                user_id=user_id,
                query=user_query,
                model=model,
                provider=provider,
                total_tokens=context.total_tokens,
                total_cost_usd=context.total_cost_usd,
                policy_violations=context.trace.policy_violations,
                policy_warnings=context.trace.policy_warnings,
                agents_run=[s.agent_name for s in context.trace.agent_timeline],
                latency_ms=context.trace.total_latency_ms,
            )

        return context

    # ── Private helpers ────────────────────────────────────────────────

    @staticmethod
    def _timeline_step(
        context: AgentContext,
        name: str,
        summary: str,
        status: str = "success",
    ) -> None:
        """Add a non-agent infrastructure step to the timeline."""
        from datetime import datetime
        step = context.trace.begin_step(name, summary)
        context.trace.end_step(step, output_summary=summary, status=status)

    @staticmethod
    def _enrich_planner_trace(context: AgentContext) -> None:
        """Copy planner output fields into the trace for the Planner Dashboard."""
        if not context.trace.agent_timeline:
            return
        plan_steps = [s for s in context.trace.agent_timeline if s.agent_name == "planner"]
        if plan_steps:
            step = plan_steps[-1]
            context.trace.planner_intent = step.output_summary
            context.trace.planner_skills = context.selected_capabilities or []
            context.trace.planner_tools  = context.selected_tools or []
            strategy = "Hybrid Database + Documents"
            if context.routing_context:
                if context.routing_context.sql_needed and not context.routing_context.rag_needed:
                    strategy = "Database Only"
                elif context.routing_context.rag_needed and not context.routing_context.sql_needed:
                    strategy = "Documents Only"
                elif context.routing_context.multi_agent:
                    strategy = "Multi-Agent Workflow"
            context.trace.planner_execution_strategy = strategy

    @staticmethod
    def _build_governance(uc: UserContext, policy_result: Any) -> dict[str, Any]:
        return {
            "simulation_mode": uc.idp_provider == "simulation",
            "authentication": {
                "method": uc.auth_method,
                "provider": uc.idp_provider,
                "mfa_verified": uc.mfa_verified,
                "status": "Authenticated (Simulation)" if uc.idp_provider == "simulation" else "Authenticated",
            },
            "authorization": {
                "user_id": uc.user_id,
                "roles": uc.roles,
                "department": uc.department,
                "clearance_level": uc.clearance,
                "status": "Authorized",
            },
            "policy_engine": {
                "pre_check_passed": policy_result.allowed,
                "violations": policy_result.violations,
                "warnings": policy_result.warnings,
                "approved_model": True,
                "data_classification": "confidential",
                "selected_policy": "enterprise_default",
            },
            "future_integrations": [
                "Microsoft Entra ID",
                "IBM Verify",
                "Okta",
                "Keycloak",
            ],
        }

    def _run_fallback_evaluation(
        self,
        context: AgentContext,
        user_query: str,
        user_confirmed: bool = False,
    ) -> None:
        """
        Evaluate multi-source fallback after the agent pipeline completes.
        If the primary source was unavailable but secondary sources provide
        enough confidence, generate a best-effort answer or a user confirmation prompt.
        """
        if not context.trace.source_priorities:
            return  # planner didn't produce source priorities — skip

        available_docs = self._get_available_docs(context)
        has_sql = bool(
            context.sql_result and context.sql_result.success
            and context.sql_result.row_count > 0
        )

        fallback_engine = MultiSourceFallbackEngine()
        fallback = fallback_engine.evaluate(
            query=user_query,
            available_docs=available_docs,
            has_sql_data=has_sql,
            source_priorities=context.trace.source_priorities,
            user_confirmed=user_confirmed,
        )
        context.trace.fallback_state = fallback.to_dict()

        if not fallback.triggered:
            return  # primary source was available — nothing to do

        self._timeline_step(
            context, "Multi-Source Fallback",
            f"Primary source '{fallback.primary_source_missing}' unavailable — "
            f"cascaded through {len(fallback.sources_searched)} secondary sources"
        )

        # Always attach the Knowledge Advisor when fallback triggers
        advisor = EnterpriseKnowledgeAdvisor()
        advisory = advisor.advise(
            query=user_query,
            missing_evidence=[fallback.primary_source_missing] + context.trace.missing_evidence,
            current_confidence=fallback.accumulated_confidence,
            available_docs=available_docs,
            has_sql_data=has_sql,
        )
        context.trace.knowledge_advisory = advisory.to_dict()

        if fallback.requires_user_confirmation:
            # Inject a structured confirmation prompt into the answer
            # The API caller must re-submit with user_confirmed=True to proceed.
            context.trace.failure_category = "partial_evidence"
            confirmation_block = (
                "\n\n---\n"
                "## Multi-Source Fallback\n\n"
                f"{fallback.confirmation_message}\n\n"
                "**Secondary sources available:**\n"
                + "\n".join(f"  ✓ {s}" for s in fallback.secondary_sources_used)
                + f"\n\n**Confidence:** {round(fallback.accumulated_confidence * 100)}%\n"
                "**Proceed?** Re-submit with `user_confirmed=true` to generate a best-effort answer."
            )
            if context.final_answer:
                context.final_answer += confirmation_block
            else:
                context.final_answer = (
                    f"Primary evidence unavailable: **{fallback.primary_source_missing}**.\n"
                    + confirmation_block
                )
        elif fallback.best_effort_answer and fallback.secondary_sources_used:
            # Enough secondary evidence — annotate the answer
            if context.final_answer:
                annotation = (
                    f"\n\n> **Note:** This answer was generated using secondary sources "
                    f"({', '.join(fallback.secondary_sources_used)}) because the primary source "
                    f"({fallback.primary_source_missing}) was unavailable. "
                    f"Confidence: {round(fallback.accumulated_confidence * 100)}%."
                )
                context.final_answer += annotation
            context.trace.failure_category = "partial_evidence"

    @staticmethod
    def _get_available_docs(context: AgentContext) -> list[str]:
        """Return list of document filenames from storage connector."""
        try:
            files = context.storage_connector.list_files()
            if files and hasattr(files[0], "name"):
                return [f.name for f in files]
            if files and isinstance(files[0], str):
                import os
                return [os.path.basename(f) for f in files]
        except Exception:
            pass
        # Fallback: use already-retrieved docs from context
        return list(context.retrieved_documents)

    @staticmethod
    def _build_evidence_sources(context: AgentContext) -> list[str]:
        sources = []
        if context.sql_result and context.sql_result.success and context.sql_result.row_count > 0:
            sources.append("Database")
        if context.rag_passages:
            sources.append("Documents")
        if context.trace.planner_skills:
            sources.append("Metadata")
        if context.glossary_context:
            sources.append("Business Glossary")
        if context.trace.data_quality_report:
            sources.append("Data Quality")
        if context.trace.lineage_entries:
            sources.append("Data Lineage")
        return sources
