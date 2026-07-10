"""
Data Quality Agent
===================
Inspects SQL query results for common data quality issues:
  - Missing / null values in result columns
  - Zero values where positive values are expected
  - Row count anomalies (empty results, single-row results)
  - Numerical outliers (values 3+ std deviations from mean)

Modular interface — extend with additional checks (freshness,
completeness, referential integrity) without changing the platform.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.explainability.trace import DataQualityReport
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("data_quality")
class DataQualityAgent(BaseAgent):
    """
    Runs data quality checks on SQL query results and produces a
    DataQualityReport stored in the explainability trace.
    """

    @property
    def agent_name(self) -> str:
        return "data_quality"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary="Running data quality checks")

        result = context.sql_result
        if not result or not result.success or not result.rows:
            report = DataQualityReport(
                total_rows=0,
                notes="No SQL results to evaluate",
                quality_score=1.0,
            )
            context.trace.data_quality_report = report
            self._end(context, step, output_summary="No data to check")
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=report,
                output_summary="No data to check",
            )

        null_cols: list[str] = []
        zero_cols: list[str] = []
        anomaly_flags: list[str] = []
        rows = result.rows
        columns = result.columns

        for col in columns:
            values = [row.get(col) for row in rows]
            null_count = sum(1 for v in values if v is None)
            null_pct = null_count / len(values) if values else 0

            if null_pct > 0.2:
                null_cols.append(col)
                context.data_quality_notes.append(
                    f"Column '{col}' has {null_pct:.0%} null values"
                )

            numeric = [float(v) for v in values if v is not None and self._is_numeric(v)]
            if numeric:
                zero_count = sum(1 for v in numeric if v == 0)
                if zero_count / len(numeric) > 0.5:
                    zero_cols.append(col)

                if len(numeric) >= 4:
                    try:
                        mean = statistics.mean(numeric)
                        stdev = statistics.stdev(numeric)
                        if stdev > 0:
                            outliers = [v for v in numeric if abs(v - mean) > 3 * stdev]
                            if outliers:
                                anomaly_flags.append(
                                    f"Column '{col}' has {len(outliers)} statistical outlier(s)"
                                )
                    except Exception:
                        pass

        if result.row_count == 0:
            anomaly_flags.append("Query returned no rows — verify filters and time ranges")
        elif result.row_count == 1:
            anomaly_flags.append("Query returned only 1 row — confirm aggregation is correct")

        # Compute quality score
        penalty = (
            len(null_cols) * 0.1
            + len(zero_cols) * 0.05
            + len(anomaly_flags) * 0.05
        )
        quality_score = round(max(0.0, 1.0 - penalty), 3)

        report = DataQualityReport(
            total_rows=result.row_count,
            null_columns=null_cols,
            zero_value_columns=zero_cols,
            anomaly_flags=anomaly_flags,
            quality_score=quality_score,
            notes="; ".join(anomaly_flags) if anomaly_flags else "All checks passed",
        )
        context.trace.data_quality_report = report

        summary = (
            f"Quality score: {quality_score:.2f} | "
            f"Null cols: {len(null_cols)} | "
            f"Anomalies: {len(anomaly_flags)}"
        )
        self._end(context, step, output_summary=summary)
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=report,
            output_summary=summary,
            metadata={"quality_score": quality_score},
        )

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False
