"""
Planner Agent — Intelligent Planning & Adaptive Orchestration
=============================================================
Implements Enhancement Document 2 (all 13 enhancements + Knowledge Coverage Score):

  1.  Intelligent Query Classification  — 8 categories
  2.  Query Feasibility Assessment      — is it answerable with current data?
  3.  Data Source Gap Analysis          — missing structured/document/connector data
  4.  Adaptive Execution Plans          — workflow built from classification
  5.  Intelligent Recommendations       — actionable next steps
  6.  Enterprise Connector Suggestions  — SAP/Workday/Oracle etc.
  7.  Confidence Engine                 — see trace.finalize()
  8.  Evidence Availability Dashboard   — required/available/missing evidence
  9.  Dynamic Agent Selection           — only invoke required agents
  10. Planner Reasoning Dashboard       — entities, evidence, strategy, cost
  11. Enterprise Readiness Score        — see trace.finalize()
  12. Data Acquisition Recommendations  — missing assets
  13. Intelligent Failure Handling      — categorised failure types
  ★   Knowledge Coverage Score          — per-source coverage with overall %
"""

from __future__ import annotations

import json
import logging
from typing import Any

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.connectors.llm.base import LLMRequest, Message, MessageRole, RoutingContext
from eio.core.registries import AgentRegistry, CapabilityRegistry

logger = logging.getLogger(__name__)

# ── Query category definitions ────────────────────────────────────────────────

QUERY_CATEGORIES = {
    "database":          "Requires structured data from a connected database (SQL query)",
    "document":          "Requires information from document repositories (RAG/vector search)",
    "hybrid":            "Requires both database data AND document evidence",
    "metadata":          "Requires schema or metadata inspection only",
    "glossary":          "Requires business glossary / term definitions only",
    "general":           "General knowledge question, no enterprise data needed",
    "unsupported":       "Cannot be answered — outside platform scope",
    "insufficient_data": "Could be answered but required data/connectors are not available",
}

# ── Connector suggestion catalogue ────────────────────────────────────────────

_CONNECTOR_CATALOGUE: list[dict[str, str]] = [
    {"name": "SAP HCM",            "type": "HR",       "use_case": "Employee master, headcount, org structure"},
    {"name": "SAP SuccessFactors",  "type": "HR",       "use_case": "Talent management, workforce planning"},
    {"name": "Workday",             "type": "HR/Finance","use_case": "HR, payroll, financial planning"},
    {"name": "Oracle HCM",         "type": "HR",       "use_case": "HR management, employee lifecycle"},
    {"name": "Salesforce CRM",     "type": "CRM",      "use_case": "Sales pipeline, customer data, revenue"},
    {"name": "ServiceNow",         "type": "ITSM",     "use_case": "IT tickets, incidents, service data"},
    {"name": "Azure SQL Database", "type": "Database", "use_case": "Enterprise relational data on Azure"},
    {"name": "Snowflake",          "type": "DataWarehouse","use_case": "Cloud data warehouse, analytics"},
    {"name": "SharePoint",         "type": "Documents","use_case": "Company documents, policies, reports"},
    {"name": "OneDrive",           "type": "Documents","use_case": "User and team documents"},
    {"name": "CSV / File Import",  "type": "Import",   "use_case": "Ad-hoc data upload from spreadsheets"},
]

# ── Known enterprise knowledge sources (for Knowledge Coverage Score) ─────────

_KNOWLEDGE_SOURCES = [
    {"name": "Financial Database",    "keywords": ["revenue", "profit", "ebitda", "margin", "expense", "quarterly", "financial", "earnings"],           "icon": "🗄️"},
    {"name": "Sales Data",            "keywords": ["sales", "pipeline", "deals", "crm", "customer", "orders"],                                            "icon": "📈"},
    {"name": "HR / Employee Data",    "keywords": ["employee", "headcount", "staff", "workforce", "hr", "salary", "payroll", "department"],               "icon": "👥"},
    {"name": "Annual Reports",        "keywords": ["annual report", "report", "strategy", "ceo", "outlook", "competitive"],                               "icon": "📄"},
    {"name": "Risk & Policy Docs",    "keywords": ["risk", "policy", "compliance", "regulatory", "audit", "governance"],                                  "icon": "🛡️"},
    {"name": "Organisation Directory","keywords": ["org", "structure", "hierarchy", "manager", "team", "division"],                                       "icon": "🏢"},
    {"name": "Product / SKU Data",    "keywords": ["product", "sku", "inventory", "catalogue", "pricing"],                                                "icon": "📦"},
    {"name": "IT / Infrastructure",   "keywords": ["system", "uptime", "incident", "ticket", "server", "infrastructure"],                                "icon": "⚙️"},
]

# ── Planner system prompt ──────────────────────────────────────────────────────

_PLANNER_SYSTEM_PROMPT = """You are the Planner Agent for an Enterprise AI Orchestration Platform.
You act like an Enterprise Solution Architect. Before executing any workflow, determine:
  - Is the question answerable with the available data?
  - Which systems contain the required information?
  - Are those systems connected?
  - Which agents are actually needed?
  - If unavailable, how can the enterprise improve its knowledge ecosystem?

Available capabilities: {capabilities}
Available agents: {agents}
Connected database tables: {db_tables}
Available documents: {doc_list}

Return ONLY valid JSON with this exact structure:
{{
  "intent": "short description of what the user wants",
  "query_category": "database|document|hybrid|metadata|glossary|general|unsupported|insufficient_data",
  "complexity": "low|medium|high",
  "is_feasible": true|false,
  "feasibility_reason": "why it is or isn't answerable with current data",
  "detected_entities": ["entity1", "entity2"],
  "required_evidence": ["evidence item 1", "evidence item 2"],
  "available_evidence": ["available item 1"],
  "missing_evidence": ["missing item 1"],
  "sql_needed": true|false,
  "rag_needed": true|false,
  "schema_discovery_needed": true|false,
  "glossary_needed": true|false,
  "data_quality_check": true|false,
  "multi_source": true|false,
  "estimated_tokens": <integer between 500 and 16000>,
  "selected_agents": ["agent1", "agent2"],
  "selected_capabilities": ["capability1"],
  "selected_tools": ["tool1"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "data_acquisition_recs": ["Connect HR database", "Upload annual reports"],
  "failure_category": "none|no_data|insufficient_data|connector_offline|permission_denied",
  "planner_reasoning": "full explanation of the execution strategy and why",
  "estimated_cost_explanation": "why this complexity/cost level was chosen"
}}

Query classification guidelines:
- database:          question requires SQL query on connected tables (financial, revenue, etc.)
- document:          question requires searching uploaded documents
- hybrid:            question requires BOTH database SQL AND document search
- metadata:          question about schema, columns, tables — no SQL execution needed
- glossary:          question about business term definitions
- general:           no enterprise data needed
- unsupported:       outside platform scope entirely
- insufficient_data: data IS needed but the required connector/table/document is NOT available

IMPORTANT for insufficient_data:
  If connected tables are: {db_tables}
  And available documents are: {doc_list}
  AND the question asks about something NOT in those tables/documents (e.g. employee count,
  headcount, HR data, sales pipeline, IT tickets), classify as "insufficient_data", set
  is_feasible=false, and populate missing_evidence and recommendations.

Always include "response_synthesis" as the last agent ONLY if is_feasible=true.
For insufficient_data queries: selected_agents should be ["metadata_discovery"] only.
"""


@AgentRegistry.register("planner")
class PlannerAgent(BaseAgent):
    """
    Intelligent Planner — acts as an Enterprise Solution Architect.
    Classifies queries, assesses feasibility, performs gap analysis,
    and builds adaptive execution plans.
    """

    @property
    def agent_name(self) -> str:
        return "planner"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary=context.user_query[:120])

        # ── Gather context for the prompt ──────────────────────────────────
        capabilities_desc = CapabilityRegistry.describe_all()
        agents_available  = AgentRegistry.available()
        db_tables         = self._get_db_tables(context)
        doc_list          = self._get_doc_list(context)

        system = _PLANNER_SYSTEM_PROMPT.format(
            capabilities=capabilities_desc,
            agents=", ".join(agents_available),
            db_tables=", ".join(db_tables) if db_tables else "none connected",
            doc_list=", ".join(doc_list[:12]) if doc_list else "none available",
        )

        request = LLMRequest(
            messages=[
                Message(
                    role=MessageRole.USER,
                    content=(
                        f"Analyze this enterprise query and produce a full planning decision:\n\n"
                        f"{context.user_query}"
                    ),
                )
            ],
            model=context.llm_provider.default_model,
            temperature=0.0,
            max_tokens=1500,
            system_prompt=system,
        )

        try:
            response = context.llm_provider.complete(request)
            context.add_tokens(response.total_tokens, response.cost_usd)
            plan = self._parse_plan(response.content)

            # ── Populate AgentContext ──────────────────────────────────────
            context.selected_agents      = plan.get("selected_agents", [])
            context.selected_tools       = plan.get("selected_tools", [])
            context.selected_capabilities = plan.get("selected_capabilities", [])

            # ── Build RoutingContext ───────────────────────────────────────
            context.routing_context = RoutingContext(
                user_query=context.user_query,
                complexity=plan.get("complexity", "medium"),
                sql_needed=plan.get("sql_needed", False),
                rag_needed=plan.get("rag_needed", False),
                multi_agent=len(context.selected_agents) > 2,
                estimated_tokens=plan.get("estimated_tokens", 2000),
            )

            # ── Write all Doc2 fields to trace ────────────────────────────
            t = context.trace
            t.query_category              = plan.get("query_category", "general")
            t.is_feasible                 = bool(plan.get("is_feasible", True))
            t.feasibility_reason          = plan.get("feasibility_reason", "")
            t.detected_entities           = plan.get("detected_entities", [])
            t.required_evidence           = plan.get("required_evidence", [])
            t.available_evidence          = plan.get("available_evidence", [])
            t.missing_evidence            = plan.get("missing_evidence", [])
            t.recommendations             = plan.get("recommendations", [])
            t.data_acquisition_recs       = plan.get("data_acquisition_recs", [])
            t.failure_category            = plan.get("failure_category", "none") or "none"
            t.planner_reasoning           = plan.get("planner_reasoning", "")
            t.estimated_cost_explanation  = plan.get("estimated_cost_explanation", "")
            t.possible_evidence_locations = self._possible_evidence_locations(plan.get("missing_evidence", []))

            # ── Connector suggestions (Doc2 #6) ───────────────────────────
            t.connector_suggestions = self._suggest_connectors(
                plan.get("missing_evidence", []),
                plan.get("query_category", ""),
            )

            # ── Knowledge Coverage Score (Signature feature) ───────────────
            t.knowledge_coverage = self._build_knowledge_coverage(
                context.user_query, db_tables, doc_list
            )

            # ── Skipped stages (Doc2 #11) ─────────────────────────────────
            t.skipped_stages = self._compute_skipped_stages(plan, context.selected_agents)

            summary = (
                f"Intent: {plan.get('intent', 'unknown')} | "
                f"Category: {t.query_category} | "
                f"Feasible: {t.is_feasible} | "
                f"Complexity: {plan.get('complexity')} | "
                f"SQL: {plan.get('sql_needed')} | "
                f"RAG: {plan.get('rag_needed')} | "
                f"Agents: {context.selected_agents}"
            )

            self._end(context, step, output_summary=summary)
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=plan,
                output_summary=summary,
                metadata={"reasoning": plan.get("planner_reasoning", "")},
            )

        except Exception as exc:
            error = f"Planner failed: {exc}"
            logger.error(error, exc_info=True)
            # Safe fallback
            context.selected_agents = [
                "metadata_discovery", "semantic_schema",
                "sql_generation", "sql_validation",
                "database_execution", "document_retrieval",
                "rag", "response_synthesis",
            ]
            context.routing_context = RoutingContext(
                user_query=context.user_query,
                complexity="high",
                sql_needed=True,
                rag_needed=True,
                estimated_tokens=4000,
            )
            context.trace.failure_category = "llm_failure"
            self._end(context, step, status="error", error=error,
                      output_summary="Fallback plan activated (planner LLM failed)")
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
                output_summary="Fallback plan activated",
            )

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _get_db_tables(context: AgentContext) -> list[str]:
        """Get available table names from the connected database."""
        try:
            if context.schema_info:
                return list(context.schema_info.tables.keys())
            schema = context.db_connector.get_schema()
            return list(schema.tables.keys())
        except Exception:
            return []

    @staticmethod
    def _get_doc_list(context: AgentContext) -> list[str]:
        """List available documents from storage connector."""
        try:
            files = context.storage_connector.list_files()
            return [f.name for f in files if hasattr(f, "name")]
        except Exception:
            try:
                # Fallback: list() may return strings directly
                files = context.storage_connector.list_files()
                if files and isinstance(files[0], str):
                    import os
                    return [os.path.basename(f) for f in files]
            except Exception:
                pass
        return []

    @staticmethod
    def _suggest_connectors(
        missing_evidence: list[str],
        query_category: str,
    ) -> list[dict[str, str]]:
        """Map missing evidence to enterprise connector suggestions."""
        suggestions: list[dict[str, str]] = []
        combined = " ".join(missing_evidence).lower() + " " + query_category.lower()
        for connector in _CONNECTOR_CATALOGUE:
            use_lower = connector["use_case"].lower()
            name_lower = connector["name"].lower()
            if any(kw in combined for kw in use_lower.split(", ")) or any(
                kw in combined for kw in name_lower.split()
            ):
                suggestions.append(connector)
        # Always suggest CSV import if data is missing
        if missing_evidence and not any(
            c["name"] == "CSV / File Import" for c in suggestions
        ):
            suggestions.append(_CONNECTOR_CATALOGUE[-1])
        return suggestions[:5]

    @staticmethod
    def _possible_evidence_locations(missing_evidence: list[str]) -> list[str]:
        if not missing_evidence:
            return []
        return [
            "SharePoint",
            "Snowflake",
            "S3",
            "Company Wiki",
            "OneDrive",
        ]

    @staticmethod
    def _build_knowledge_coverage(
        query: str,
        db_tables: list[str],
        doc_list: list[str],
    ) -> dict[str, Any]:
        """
        Signature feature: evaluate which knowledge sources are relevant to the
        query and which are connected. Returns per-source availability + overall %.
        """
        query_lower = query.lower()
        all_docs_lower = " ".join(doc_list).lower()
        all_tables_lower = " ".join(db_tables).lower()

        source_results = []
        available_count = 0

        for src in _KNOWLEDGE_SOURCES:
            relevant = any(kw in query_lower for kw in src["keywords"])
            if not relevant:
                # Always include Financial and Annual Reports as baseline
                relevant = src["name"] in ("Financial Database", "Annual Reports")

            if not relevant:
                continue

            # Is it available?
            if src["name"] == "Financial Database":
                available = bool(db_tables)
            elif src["name"] in ("Annual Reports", "Risk & Policy Docs"):
                available = any(
                    ext in all_docs_lower
                    for ext in (".pdf", ".txt", "report", "policy", "annual")
                )
            elif src["name"] == "HR / Employee Data":
                available = any(
                    kw in all_tables_lower
                    for kw in ("employee", "hr", "staff", "headcount")
                ) or "employee" in all_docs_lower
            elif src["name"] == "Sales Data":
                available = any(kw in all_tables_lower for kw in ("sales", "crm", "order"))
            else:
                # Generic: check if any doc or table mentions source keywords
                available = any(
                    kw in all_tables_lower or kw in all_docs_lower
                    for kw in src["keywords"][:3]
                )

            source_results.append({
                "name":      src["name"],
                "icon":      src["icon"],
                "available": available,
                "relevant":  relevant,
            })
            if available:
                available_count += 1

        total = len(source_results)
        overall_pct = round((available_count / total) * 100) if total else 0

        # Build recommendation
        missing_names = [s["name"] for s in source_results if not s["available"]]
        if missing_names:
            rec = f"Connect {', '.join(missing_names[:3])} to improve answer quality."
        else:
            rec = "All relevant knowledge sources are connected."

        return {
            "title": "Enterprise Knowledge Map",
            "sources":      source_results,
            "available":    available_count,
            "total":        total,
            "overall_pct":  overall_pct,
            "recommendation": rec,
        }

    @staticmethod
    def _compute_skipped_stages(plan: dict, selected_agents: list[str]) -> list[dict[str, str]]:
        """Doc2 #11: Identify which pipeline stages were skipped and why."""
        all_stages = {
            "metadata_discovery":     "Schema not needed for this query type",
            "semantic_schema":        "Business term mapping not required",
            "sql_generation":         "No structured database query needed",
            "sql_validation":         "No SQL was generated",
            "database_execution":     "No SQL to execute",
            "document_retrieval":     "No document search required",
            "rag":                    "No vector search required",
            "data_quality":           "Data quality check skipped",
            "lineage":                "Lineage tracking not required",
            "business_glossary":      "Business glossary not needed for this query",
            "response_synthesis":     "Query was not feasible — synthesis skipped",
        }
        skipped = []
        for stage, default_reason in all_stages.items():
            if stage not in selected_agents:
                # Build a smarter reason
                if stage == "sql_generation" and not plan.get("sql_needed"):
                    reason = "Planner determined no SQL query is needed"
                elif stage == "rag" and not plan.get("rag_needed"):
                    reason = "Planner determined no document search is needed"
                elif stage == "response_synthesis" and not plan.get("is_feasible", True):
                    reason = "Query infeasible — synthesis skipped to avoid hallucination"
                elif stage == "data_quality" and not plan.get("data_quality_check"):
                    reason = "Data quality check not required for this query"
                else:
                    reason = default_reason
                skipped.append({"stage": stage, "reason": reason})
        return skipped

    @staticmethod
    def _parse_plan(content: str) -> dict:
        """Extract JSON from LLM response, handling markdown code fences."""
        text = content.strip()
        if "```" in text:
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise
