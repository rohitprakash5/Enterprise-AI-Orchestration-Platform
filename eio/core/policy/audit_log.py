"""
Audit Logger
=============
Append-only JSON Lines audit log writer.
Each request produces one audit record that captures:
  - timestamp, user, query, model used, cost, tokens, policy violations
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """Thread-safe append-only JSON Lines audit log."""

    def __init__(self, log_path: str) -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        request_id: str,
        user_id: str,
        query: str,
        model: str,
        provider: str,
        total_tokens: int,
        total_cost_usd: float,
        policy_violations: list[str],
        policy_warnings: list[str],
        agents_run: list[str],
        latency_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Write one audit record to the log file."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "user_id": user_id or "anonymous",
            "query_preview": query[:200],
            "model": model,
            "provider": provider,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 6),
            "latency_ms": round(latency_ms, 1),
            "agents_run": agents_run,
            "policy_violations": policy_violations,
            "policy_warnings": policy_warnings,
            **(metadata or {}),
        }
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.error(f"Failed to write audit log: {exc}")

    def read_recent(self, n: int = 100) -> list[dict[str, Any]]:
        """Read the N most recent audit records."""
        if not self._path.exists():
            return []
        records = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in reversed(lines[-n:]):
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        except Exception as exc:
            logger.error(f"Failed to read audit log: {exc}")
        return records
