"""
EIO FastAPI Application
========================
Entry point for the EIO REST API.

Endpoints:
  POST  /api/v1/query                  — Execute a query through the orchestrator
  GET   /api/v1/health                 — API health
  GET   /api/v1/health/connectors      — Per-connector health
  GET   /api/v1/config                 — Active connector and model configuration

Application lifespan:
  - Connects to all configured connectors
  - Seeds the demo database if it doesn't exist
  - Initializes the ChromaDB vector collection
  - Warms up the Orchestrator
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eio.api.routes import config, health, models, query

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("EIO_LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("EIO API starting up...")
    await _startup(app)
    yield
    logger.info("EIO API shutting down...")


async def _startup(app: FastAPI) -> None:
    """
    Initialize all platform components:
    1. Seed demo database
    2. Connect DB/storage/LLM connectors
    3. Initialize ChromaDB
    4. Create the Orchestrator
    """
    from eio.connectors.databases import ConnectorRegistry as DBRegistry
    from eio.connectors.llm import LLMRegistry
    from eio.connectors.storage import StorageRegistry
    from eio.core.orchestrator.orchestrator import Orchestrator

    # ── 1. Seed demo data ───────────────────────────────────────────────
    try:
        from eio.data.demo.seed_financial_db import seed
        seed()
    except Exception as exc:
        logger.warning(f"Demo seed skipped: {exc}")

    # ── 2. Connect database ─────────────────────────────────────────────
    active_db = os.getenv("EIO_ACTIVE_DB", "sqlite")
    db_connector = DBRegistry.get(
        active_db,
        db_path=os.getenv("EIO_SQLITE_PATH", "eio/data/demo/financial.db"),
    )
    db_connector.connect()
    logger.info(f"Database connector: {active_db}")

    # ── 3. Connect storage ──────────────────────────────────────────────
    active_storage = os.getenv("EIO_ACTIVE_STORAGE", "local")
    storage_connector = StorageRegistry.get(
        active_storage,
        root_path=os.getenv("EIO_LOCAL_STORAGE_PATH", "eio/data/demo/documents"),
    )
    logger.info(f"Storage connector: {active_storage}")

    # ── 4. Connect LLM ──────────────────────────────────────────────────
    active_llm = os.getenv("EIO_ACTIVE_LLM", "gpt_oss")
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    hf_token   = os.getenv("HF_TOKEN", "").strip()

    # Auto-promote to openai if key is set and user left default
    if active_llm == "gpt_oss" and openai_key and not hf_token:
        active_llm = "openai"
        logger.info("OPENAI_API_KEY detected — promoting EIO_ACTIVE_LLM to 'openai'")

    if active_llm == "openai":
        llm_provider = LLMRegistry.get("openai", api_key=openai_key)
    elif active_llm == "gpt_oss":
        llm_provider = LLMRegistry.get("gpt_oss",
                                        hf_token=hf_token,
                                        endpoint_url=os.getenv("EIO_GPTOSS_ENDPOINT_URL", ""),
                                        model_id=os.getenv("EIO_GPTOSS_MODEL_ID", "openai/gpt-oss-20b"))
    else:
        llm_provider = LLMRegistry.get(active_llm)

    logger.info(f"LLM provider: {active_llm} | health: {llm_provider.health_check().get('mode','?')}")

    # ── 5. Initialize ChromaDB ──────────────────────────────────────────
    chroma_path = os.getenv("EIO_CHROMA_PATH", "eio/data/chroma")
    chroma_collection = os.getenv("EIO_CHROMA_COLLECTION", "eio_documents")
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    collection = chroma_client.get_or_create_collection(
        name=chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"ChromaDB collection '{chroma_collection}' ready ({collection.count()} chunks)")

    # ── 6. Create Orchestrator ──────────────────────────────────────────
    orchestrator = Orchestrator(
        db_connector=db_connector,
        storage_connector=storage_connector,
        llm_provider=llm_provider,
        vector_collection=collection,
    )

    # Store in app state for access by route handlers
    app.state.orchestrator = orchestrator
    app.state.db_connector = db_connector
    app.state.storage_connector = storage_connector
    app.state.llm_provider = llm_provider

    logger.info("EIO Orchestrator ready")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise Intelligence Orchestrator (EIO)",
        description=(
            "Multi-agent AI orchestration platform that coordinates specialized agents, "
            "heterogeneous data sources, and multiple LLM providers to answer business "
            "questions with explainable reasoning."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://eio-ui:8501",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(query.router,  prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(config.router, prefix="/api/v1")
    app.include_router(models.router, prefix="/api/v1")

    return app


app = create_app()
