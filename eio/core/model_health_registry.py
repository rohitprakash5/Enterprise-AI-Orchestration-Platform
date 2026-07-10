"""
Model Health Registry
======================
Tracks runtime health status of each registered LLM provider.
The AI Decision Engine skips unhealthy models automatically.

Health entries are updated:
  - At API startup (initial probe)
  - After every successful/failed LLM call (via HealthRegistry.record_call)
  - Via background probe (optional, set EIO_HEALTH_PROBE_INTERVAL_S)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ModelHealthEntry:
    model_id:            str
    provider:            str
    display_name:        str
    status:              str = "unknown"      # "online" | "offline" | "degraded" | "unknown"
    avg_latency_ms:      float = 0.0
    last_latency_ms:     float = 0.0
    success_count:       int = 0
    error_count:         int = 0
    last_success:        datetime | None = None
    last_error:          datetime | None = None
    last_error_msg:      str = ""
    available:           bool = True          # False = skip this model

    @property
    def error_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.error_count / total if total > 0 else 0.0

    @property
    def health_label(self) -> str:
        if self.status == "online" and self.error_rate < 0.1:
            return "Healthy"
        if self.status == "degraded" or self.error_rate >= 0.1:
            return "Degraded"
        if self.status == "offline":
            return "Offline"
        return "Unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":        self.model_id,
            "provider":        self.provider,
            "display_name":    self.display_name,
            "status":          self.status,
            "health_label":    self.health_label,
            "avg_latency_ms":  round(self.avg_latency_ms, 1),
            "last_latency_ms": round(self.last_latency_ms, 1),
            "success_count":   self.success_count,
            "error_count":     self.error_count,
            "error_rate_pct":  round(self.error_rate * 100, 1),
            "last_success":    self.last_success.isoformat() if self.last_success else None,
            "last_error":      self.last_error.isoformat() if self.last_error else None,
            "last_error_msg":  self.last_error_msg,
            "available":       self.available,
        }


class ModelHealthRegistry:
    """
    Thread-safe in-memory health registry.
    Initialized from ModelCapabilityRegistry profiles at startup.
    """

    _entries: dict[str, ModelHealthEntry] = {}

    @classmethod
    def initialize_from_profiles(cls) -> None:
        from eio.core.model_capability_registry import ModelCapabilityRegistry
        for profile in ModelCapabilityRegistry.all():
            if profile.model_id not in cls._entries:
                cls._entries[profile.model_id] = ModelHealthEntry(
                    model_id=profile.model_id,
                    provider=profile.provider,
                    display_name=profile.display_name,
                    avg_latency_ms=profile.avg_latency_ms,
                    status="unknown",
                )

    @classmethod
    def record_call(
        cls,
        model_id: str,
        latency_ms: float,
        success: bool,
        error_msg: str = "",
    ) -> None:
        entry = cls._entries.get(model_id)
        if not entry:
            return
        if success:
            entry.success_count += 1
            entry.last_success = datetime.utcnow()
            entry.status = "online"
            # Rolling average latency
            n = entry.success_count
            entry.avg_latency_ms = (
                (entry.avg_latency_ms * (n - 1) + latency_ms) / n
            )
            entry.last_latency_ms = latency_ms
        else:
            entry.error_count += 1
            entry.last_error = datetime.utcnow()
            entry.last_error_msg = error_msg[:200]
            total = entry.success_count + entry.error_count
            if entry.error_count / total > 0.5:
                entry.status = "offline"
            else:
                entry.status = "degraded"

    @classmethod
    def mark_online(cls, model_id: str) -> None:
        if model_id in cls._entries:
            cls._entries[model_id].status = "online"
            cls._entries[model_id].available = True

    @classmethod
    def mark_offline(cls, model_id: str, reason: str = "") -> None:
        if model_id in cls._entries:
            cls._entries[model_id].status = "offline"
            cls._entries[model_id].available = False
            cls._entries[model_id].last_error_msg = reason

    @classmethod
    def is_available(cls, model_id: str) -> bool:
        entry = cls._entries.get(model_id)
        return entry.available if entry else False

    @classmethod
    def get(cls, model_id: str) -> ModelHealthEntry | None:
        return cls._entries.get(model_id)

    @classmethod
    def all(cls) -> list[ModelHealthEntry]:
        return list(cls._entries.values())

    @classmethod
    def all_dicts(cls) -> list[dict[str, Any]]:
        return [e.to_dict() for e in cls._entries.values()]
