"""
Metadata Discovery Agent
=========================
Introspects the active database and returns a structured schema.
Used by SemanticSchemaAgent and SQLGenerationAgent to build
accurate SQL queries with correct table/column names.
"""

from __future__ import annotations

import logging

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("metadata_discovery")
class MetadataDiscoveryAgent(BaseAgent):
    """
    Calls DatabaseConnector.get_schema() and stores the result
    in AgentContext for downstream agents.
    """

    @property
    def agent_name(self) -> str:
        return "metadata_discovery"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary="Discovering database schema")

        try:
            schema = context.db_connector.get_schema()
            context.schema_info = schema
            context.schema_context_str = schema.to_context_string()

            # Record lineage
            context.trace.add_lineage(
                source_type="database",
                source_name=schema.database_name,
                operation="schema_introspection",
                details=f"Discovered {len(schema.tables)} tables",
            )

            table_names = list(schema.tables.keys())
            summary = (
                f"Discovered {len(table_names)} tables: {', '.join(table_names)}"
            )

            self._end(context, step, output_summary=summary)
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=schema,
                output_summary=summary,
                metadata={"table_count": len(table_names), "tables": table_names},
            )

        except Exception as exc:
            error = f"Schema discovery failed: {exc}"
            logger.error(error, exc_info=True)
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
                output_summary="Schema discovery failed",
            )
