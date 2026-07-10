"""
Lineage Agent
==============
Records and summarizes data lineage throughout the request lifecycle.
Answers: what data was accessed, from where, and how was it used?

Modular interface — extend with full column-level lineage,
data catalog integration, or OpenLineage event emission.
"""

from __future__ import annotations

import logging

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("lineage")
class LineageAgent(BaseAgent):
    """
    Summarizes accumulated data lineage from the AgentContext trace.
    Lineage entries are written by individual agents as they execute.
    This agent produces the final consolidated lineage summary.
    """

    @property
    def agent_name(self) -> str:
        return "lineage"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary="Compiling lineage summary")

        entries = context.trace.lineage_entries
        if not entries:
            self._end(context, step, output_summary="No lineage entries recorded")
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=[],
                output_summary="No lineage entries",
            )

        # Group entries by source type
        by_type: dict[str, list[str]] = {}
        for entry in entries:
            by_type.setdefault(entry.source_type, []).append(
                f"{entry.source_name} ({entry.operation})"
            )

        # Build lineage notes for context
        lines: list[str] = []
        for source_type, items in by_type.items():
            lines.append(f"{source_type.title()} Sources:")
            for item in items:
                lines.append(f"  - {item}")
        context.lineage_notes = lines

        summary = (
            f"Lineage: {len(entries)} entries across "
            f"{', '.join(by_type.keys())}"
        )
        self._end(context, step, output_summary=summary,
                  metadata={"entry_count": len(entries), "source_types": list(by_type.keys())})
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=entries,
            output_summary=summary,
        )
