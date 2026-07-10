"""
SQL Generation Agent
=====================
Generates SQL from the user's natural language query using:
  - Enriched schema context (from MetadataDiscovery + SemanticSchema)
  - Business glossary mappings
  - The selected LLM

Produces a single SQL SELECT statement targeted at the configured database.
The generated SQL is stored in AgentContext.sql_generated for
downstream validation and execution.
"""

from __future__ import annotations

import logging

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.connectors.llm.base import LLMRequest, Message, MessageRole
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)

_SQL_SYSTEM_PROMPT = """You are an expert SQL analyst for an enterprise financial database.

Generate a single, correct SQL SELECT query that answers the user's question.

Schema and available data:
{schema}

Rules:
- Return ONLY the SQL query, no explanation, no markdown fences
- Use only SELECT statements — no INSERT, UPDATE, DELETE, DROP
- Use proper SQL syntax compatible with SQLite
- Use table aliases for readability
- Add LIMIT 100 if the query might return many rows
- Use SUM(), AVG(), COUNT(), GROUP BY, ORDER BY as appropriate
- If the question references time periods, use WHERE clauses on the `year` and `quarter` columns
- If the question compares multiple metrics, use a single query with multiple columns
- The "Sample values" section above confirms exactly what data exists — use it to verify filters
- For revenue/financial questions, join `companies` on company_id to filter by company name
- Company names are in the `companies.name` column (e.g. 'Apex Analytics Corp')
- Quarter values are integers 1, 2, 3, 4 (Q1=1, Q2=2, Q3=3, Q4=4)
- ALWAYS generate SQL when the schema and sample values confirm the data exists

If the question cannot be answered with SQL from the available schema, return:
CANNOT_GENERATE: <reason>
"""


@AgentRegistry.register("sql_generation")
class SQLGenerationAgent(BaseAgent):
    """
    Converts natural language to SQL using the active LLM.
    Relies on enriched schema context from MetadataDiscovery + SemanticSchema.
    """

    @property
    def agent_name(self) -> str:
        return "sql_generation"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(
            context,
            input_summary=f"Generating SQL for: {context.user_query[:80]}",
        )

        if not context.schema_context_str:
            self._end(context, step, output_summary="No schema — SQL generation skipped",
                      status="error")
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error="No schema context available for SQL generation",
            )

        # Determine which model to use
        model = (
            context.routing_decision.model
            if context.routing_decision
            else context.llm_provider.default_model
        )

        system = _SQL_SYSTEM_PROMPT.format(schema=context.schema_context_str)
        request = LLMRequest(
            messages=[
                Message(
                    role=MessageRole.USER,
                    content=(
                        f"Question: {context.user_query}\n\n"
                        f"Generate SQL to answer this question using the schema above."
                    ),
                )
            ],
            model=model,
            temperature=0.0,
            max_tokens=512,
            system_prompt=system,
        )

        try:
            response = context.llm_provider.complete(request)
            context.add_tokens(response.total_tokens, response.cost_usd)

            sql = response.content.strip()

            # Handle cannot-generate case
            if sql.upper().startswith("CANNOT_GENERATE"):
                reason = sql.split(":", 1)[-1].strip() if ":" in sql else sql
                self._end(context, step,
                          output_summary=f"SQL generation not possible: {reason}",
                          status="error")
                return AgentResult(
                    agent_name=self.agent_name,
                    success=False,
                    error=f"Cannot generate SQL: {reason}",
                )

            # Strip markdown fences if model added them
            if "```" in sql:
                lines = sql.split("\n")
                sql = "\n".join(
                    l for l in lines if not l.strip().startswith("```")
                ).strip()

            context.sql_generated = sql
            context.trace.sql_generated = sql

            summary = f"Generated SQL ({len(sql)} chars)"
            self._end(context, step, output_summary=summary,
                      metadata={"sql_preview": sql[:200]})
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=sql,
                output_summary=summary,
                metadata={"sql": sql, "model_used": model},
            )

        except Exception as exc:
            error = f"SQL generation failed: {exc}"
            logger.error(error, exc_info=True)
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
            )
