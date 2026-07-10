"""
Models Route
=============
GET /api/v1/models          — List all registered model capability profiles
GET /api/v1/models/health   — Live health status of all registered models
GET /api/v1/models/{id}     — Single model profile + health
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from eio.core.model_capability_registry import ModelCapabilityRegistry
from eio.core.model_health_registry import ModelHealthRegistry

router = APIRouter(tags=["Models"])


@router.get("/models")
async def list_models() -> dict:
    """Return all registered model capability profiles."""
    profiles = [
        {
            "model_id":           p.model_id,
            "display_name":       p.display_name,
            "provider":           p.provider,
            "capabilities":       p.capability_tags(),
            "context_window":     p.context_window,
            "cost_per_1k_input":  p.cost_per_1k_input,
            "cost_per_1k_output": p.cost_per_1k_output,
            "avg_latency_ms":     p.avg_latency_ms,
            "governance_approved": p.governance_approved,
            "requires_api_key":   p.requires_api_key,
            "local_only":         p.local_only,
            "reasoning_score":    p.reasoning_score,
            "sql_score":          p.sql_score,
            "accuracy_score":     p.accuracy_score,
            "notes":              p.notes,
        }
        for p in ModelCapabilityRegistry.all()
    ]
    return {
        "count":    len(profiles),
        "profiles": profiles,
    }


@router.get("/models/health")
async def models_health() -> dict:
    """Return live health status for all registered models."""
    return {
        "count":   len(ModelHealthRegistry.all()),
        "entries": ModelHealthRegistry.all_dicts(),
    }


@router.get("/models/{model_id:path}")
async def get_model(model_id: str) -> dict:
    """Return capability profile + health entry for a specific model."""
    profile = ModelCapabilityRegistry.get(model_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    health = ModelHealthRegistry.get(model_id)
    return {
        "profile": {
            "model_id":           profile.model_id,
            "display_name":       profile.display_name,
            "provider":           profile.provider,
            "capabilities":       profile.capability_tags(),
            "context_window":     profile.context_window,
            "cost_per_1k_input":  profile.cost_per_1k_input,
            "cost_per_1k_output": profile.cost_per_1k_output,
            "avg_latency_ms":     profile.avg_latency_ms,
            "governance_approved": profile.governance_approved,
            "reasoning_score":    profile.reasoning_score,
            "sql_score":          profile.sql_score,
            "accuracy_score":     profile.accuracy_score,
            "notes":              profile.notes,
        },
        "health": health.to_dict() if health else None,
    }
