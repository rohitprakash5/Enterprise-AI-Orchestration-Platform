"""
Policy Engine
==============
Enforces enterprise governance rules at three checkpoints:
  1. Pre-routing   — token budget, cost limit, model approval
  2. Pre-execution — SQL keyword blocking
  3. Post-synthesis — PII detection and masking in output

Policy rules are loaded from policies.yaml so they can be changed
without touching application code (or mounted as a ConfigMap in K8s).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PolicyResult(BaseModel):
    """Result of a policy evaluation checkpoint."""

    allowed: bool = True
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    pii_detected: list[str] = Field(default_factory=list)
    redacted_content: str | None = None

    def merge(self, other: "PolicyResult") -> "PolicyResult":
        """Combine two policy results (used when running multiple checks)."""
        return PolicyResult(
            allowed=self.allowed and other.allowed,
            violations=self.violations + other.violations,
            warnings=self.warnings + other.warnings,
            pii_detected=self.pii_detected + other.pii_detected,
            redacted_content=other.redacted_content or self.redacted_content,
        )


class PolicyEngine:
    """
    Stateless policy evaluator.
    Loads configuration from YAML on construction and caches it.
    Thread-safe for concurrent requests.
    """

    def __init__(self, config_path: str | None = None) -> None:
        path = config_path or os.getenv(
            "EIO_POLICY_CONFIG", "eio/core/policy/policies.yaml"
        )
        self._config = self._load_config(Path(path))
        self._pii_patterns = self._compile_pii_patterns()

    # ── Config loading ─────────────────────────────────────────────────────

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _compile_pii_patterns(self) -> dict[str, re.Pattern]:
        patterns: dict[str, re.Pattern] = {}
        if not self._config.get("pii_detection_enabled", True):
            return patterns
        for name, pattern in self._config.get("pii_patterns", {}).items():
            try:
                patterns[name] = re.compile(pattern, re.IGNORECASE)
            except re.error:
                pass
        return patterns

    # ── Checkpoint 1: Pre-routing ──────────────────────────────────────────

    def check_routing(
        self,
        estimated_tokens: int,
        estimated_cost_usd: float,
        model_name: str,
    ) -> PolicyResult:
        """
        Validate before model routing.
        Checks: token budget, cost limit, model approval list.
        """
        violations: list[str] = []
        warnings: list[str] = []

        max_tokens = int(self._config.get("max_tokens_per_request", 16000))
        if estimated_tokens > max_tokens:
            violations.append(
                f"Token estimate {estimated_tokens} exceeds policy limit {max_tokens}"
            )

        max_cost = float(self._config.get("max_cost_usd_per_request", 0.50))
        if estimated_cost_usd > max_cost:
            violations.append(
                f"Estimated cost ${estimated_cost_usd:.4f} exceeds policy limit ${max_cost:.2f}"
            )

        approved = self._config.get("approved_models", [])
        if approved and model_name:
            # Accept "org/model-id" if either the full ID or the short ID after "/" is approved
            short_name = model_name.split("/")[-1] if "/" in model_name else model_name
            if model_name not in approved and short_name not in approved:
                violations.append(
                    f"Model '{model_name}' is not in the approved models list"
                )

        return PolicyResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    # ── Checkpoint 2: Pre-execution SQL check ─────────────────────────────

    def check_sql(self, sql: str) -> PolicyResult:
        """
        Block dangerous SQL keywords before execution.
        Only SELECT queries are allowed in the demo environment.
        """
        blocked = self._config.get("blocked_sql_keywords", [
            "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
            "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
        ])

        sql_upper = sql.upper()
        found = [kw for kw in blocked if re.search(rf"\b{kw}\b", sql_upper)]

        if found:
            return PolicyResult(
                allowed=False,
                violations=[f"SQL contains blocked keyword(s): {', '.join(found)}"],
            )
        return PolicyResult(allowed=True)

    # ── Checkpoint 3: Post-synthesis PII check ────────────────────────────

    def check_pii(self, content: str) -> PolicyResult:
        """
        Scan response content for PII patterns.
        Detected PII is redacted with [REDACTED:<type>].
        """
        if not self._pii_patterns:
            return PolicyResult(allowed=True, redacted_content=content)

        detected: list[str] = []
        redacted = content
        for pii_type, pattern in self._pii_patterns.items():
            matches = pattern.findall(redacted)
            if matches:
                detected.append(pii_type)
                redacted = pattern.sub(f"[REDACTED:{pii_type.upper()}]", redacted)

        return PolicyResult(
            allowed=True,   # PII detection is warn-only; content is returned redacted
            pii_detected=detected,
            warnings=[f"PII detected and redacted: {', '.join(detected)}"] if detected else [],
            redacted_content=redacted,
        )

    # ── Property accessors ─────────────────────────────────────────────────

    @property
    def max_sql_result_rows(self) -> int:
        return int(self._config.get("max_sql_result_rows", 1000))

    @property
    def require_sql_validation(self) -> bool:
        return bool(self._config.get("require_sql_validation", True))

    @property
    def audit_log_enabled(self) -> bool:
        return bool(self._config.get("audit_log_enabled", True))

    @property
    def audit_log_path(self) -> str:
        return str(self._config.get("audit_log_path", "eio/data/audit/audit.log"))
