"""Health Routes"""
from __future__ import annotations
from fastapi import APIRouter, Request

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "eio-api", "version": "0.1.0"}


@router.get("/health/connectors")
async def health_connectors(request: Request) -> dict:
    db = request.app.state.db_connector.health_check()
    storage = request.app.state.storage_connector.health_check()
    llm = request.app.state.llm_provider.health_check()
    overall = all(c.get("status") == "ok" for c in [db, storage])
    return {
        "status": "ok" if overall else "degraded",
        "connectors": {"database": db, "storage": storage, "llm": llm},
    }
