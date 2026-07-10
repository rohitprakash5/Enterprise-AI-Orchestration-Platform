"""
Database Execution Agent
=========================
Executes validated SQL through the active DatabaseConnector.
Stores the QueryResult in AgentContext for downstream agents.

Only executes if SQLValidationAgent has approved the SQL
(context.sql_validated == True).
"""

from __future__ import annotations

import logging

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("database_execution")
class DatabaseExecutionAgent(BaseAgent):
    """
    Executes validated SQL via the injected DatabaseConnector.
    Records data lineage for every executed query.
    """

    @property
    def agent_name(self) -> str:
        return "database_execution"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(
            context,
            input_summary=f"Executing SQL: {context.sql_generated[:80]}",
        )

        if not context.sql_generated:
            self._end(context, step, output_summary="No SQL to execute — skipped")
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output_summary="No SQL to execute",
            )

        if not context.sql_validated:
            error = "SQL was not validated — execution blocked by policy"
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
                output_summary=error,
            )

        try:
            result = context.db_connector.execute_query(context.sql_generated)

            if not result.success:
                error = f"Query execution error: {result.error}"
                self._end(context, step, status="error", error=error)
                return AgentResult(
                    agent_name=self.agent_name,
                    success=False,
                    error=error,
                )

            context.sql_result = result

            # Record lineage
            schema_name = (
                context.schema_info.database_name
                if context.schema_info
                else "database"
            )
            context.trace.add_lineage(
                source_type="database",
                source_name=schema_name,
                operation="sql_query",
                details=(
                    f"Returned {result.row_count} rows in {result.execution_time_ms:.1f}ms"
                ),
            )

            summary = (
                f"Returned {result.row_count} row(s) in {result.execution_time_ms:.1f}ms"
            )
            self._end(context, step, output_summary=summary,
                      metadata={"row_count": result.row_count,
                                "execution_time_ms": result.execution_time_ms})
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=result,
                output_summary=summary,
            )

        except Exception as exc:
            error = f"Database execution failed: {exc}"
            logger.error(error, exc_info=True)
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
            )
