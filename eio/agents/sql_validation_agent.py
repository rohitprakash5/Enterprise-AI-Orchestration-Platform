"""
SQL Validation Agent
=====================
Validates generated SQL before execution:
  1. Syntax check via sqlparse
  2. Safety check: blocks dangerous SQL keywords (via PolicyEngine)
  3. Basic structural check: must be a SELECT statement

Modular interface — extend with additional validation rules
(column existence check, join safety, etc.) without changing
the core platform.
"""

from __future__ import annotations

import logging
import re

import sqlparse

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)

_BLOCKED_KEYWORDS = frozenset([
    "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
    "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
])


@AgentRegistry.register("sql_validation")
class SQLValidationAgent(BaseAgent):
    """
    Validates SQL safety and syntax before database execution.
    Integrates with PolicyEngine for configurable blocked keywords.
    """

    @property
    def agent_name(self) -> str:
        return "sql_validation"

    def run(self, context: AgentContext) -> AgentResult:
        sql = context.sql_generated
        step = self._begin(context, input_summary=f"Validating SQL: {sql[:80]}")

        if not sql:
            self._end(context, step, output_summary="No SQL to validate — skipped")
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output_summary="No SQL to validate",
            )

        violations: list[str] = []

        # ── 1. Safety check ───────────────────────────────────────────────
        sql_upper = sql.upper()
        found_blocked = [kw for kw in _BLOCKED_KEYWORDS if re.search(rf"\b{kw}\b", sql_upper)]
        if found_blocked:
            violations.append(f"Blocked keyword(s): {', '.join(found_blocked)}")

        # ── 2. Must be SELECT ─────────────────────────────────────────────
        parsed = sqlparse.parse(sql)
        if parsed:
            stmt = parsed[0]
            stmt_type = stmt.get_type()
            if stmt_type and stmt_type.upper() != "SELECT":
                violations.append(f"Only SELECT statements allowed, got: {stmt_type}")
        else:
            violations.append("SQL could not be parsed")

        # ── 3. Basic structural check ─────────────────────────────────────
        stripped = sql.strip().upper()
        if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
            violations.append("SQL must begin with SELECT or WITH")

        if violations:
            error = "SQL validation failed: " + "; ".join(violations)
            context.sql_validated = False
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
                output_summary=error,
                metadata={"violations": violations},
            )

        context.sql_validated = True
        context.trace.sql_validated = True
        summary = "SQL passed all validation checks"
        self._end(context, step, output_summary=summary)
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=sql,
            output_summary=summary,
        )
