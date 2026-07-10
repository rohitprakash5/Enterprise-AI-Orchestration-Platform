"""
Migration & Reconciliation Agent
==================================
Compares query results across multiple data sources to validate
consistency during migrations or cross-system analytics.

Modular interface — extend with tolerance-based comparison,
column-level diff, row-hash comparison, or cross-schema reconciliation.

Current implementation: basic row/column count comparison between
two QueryResult objects stored in AgentContext.
"""

from __future__ import annotations

import logging
from typing import Any

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.connectors.databases.base import QueryResult
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("migration_reconciliation")
class MigrationReconciliationAgent(BaseAgent):
    """
    Reconciles data between two sources.

    To use:
      1. Store the primary result in context.sql_result (populated by DatabaseExecutionAgent)
      2. Store the secondary result in context.metadata["secondary_result"]
      3. This agent computes the reconciliation summary

    Extend this agent with tolerance thresholds, column-level diffs,
    and alerting without changing the core platform.
    """

    @property
    def agent_name(self) -> str:
        return "migration_reconciliation"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary="Reconciling data sources")

        primary = context.sql_result
        # Secondary result is injected via metadata for multi-source requests
        secondary: QueryResult | None = None
        if hasattr(context, "_secondary_result"):
            secondary = getattr(context, "_secondary_result")

        if not primary:
            self._end(context, step, output_summary="No primary result to reconcile — skipped")
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output_summary="No data available for reconciliation",
            )

        if not secondary:
            self._end(
                context, step,
                output_summary="Single-source request — reconciliation not applicable",
            )
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output_summary="Single-source request, reconciliation skipped",
                metadata={"primary_row_count": primary.row_count},
            )

        # Basic reconciliation
        findings: list[str] = []
        report: dict[str, Any] = {
            "primary_row_count": primary.row_count,
            "secondary_row_count": secondary.row_count,
            "column_match": primary.columns == secondary.columns,
        }

        if primary.row_count != secondary.row_count:
            findings.append(
                f"Row count mismatch: primary={primary.row_count}, "
                f"secondary={secondary.row_count}"
            )
        if primary.columns != secondary.columns:
            findings.append(
                f"Column mismatch: primary={primary.columns}, "
                f"secondary={secondary.columns}"
            )

        report["findings"] = findings
        report["reconciled"] = len(findings) == 0

        summary = (
            "Reconciliation PASSED — sources match"
            if not findings
            else f"Reconciliation FAILED: {'; '.join(findings)}"
        )
        self._end(context, step, output_summary=summary, metadata=report)
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=report,
            output_summary=summary,
        )
