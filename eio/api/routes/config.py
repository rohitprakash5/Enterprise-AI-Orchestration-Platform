"""Config Route"""
from __future__ import annotations
import os
from fastapi import APIRouter
from eio.connectors.databases import ConnectorRegistry as DBReg
from eio.connectors.storage import StorageRegistry as StorageReg
from eio.connectors.llm import LLMRegistry

router = APIRouter(tags=["Config"])


@router.get("/config")
async def get_config() -> dict:
    return {
        "active_llm": os.getenv("EIO_ACTIVE_LLM", "openai"),
        "active_db": os.getenv("EIO_ACTIVE_DB", "sqlite"),
        "active_storage": os.getenv("EIO_ACTIVE_STORAGE", "local"),
        "available_llm_providers": LLMRegistry.available(),
        "available_db_connectors": DBReg.available(),
        "available_storage_connectors": StorageReg.available(),
        "policy_config": os.getenv("EIO_POLICY_CONFIG", "eio/core/policy/policies.yaml"),
    }
