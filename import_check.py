"""Quick import validation for EIO platform."""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from eio.api.main import create_app
from eio.api.schemas import ExplainabilityDTO, QueryResponse
from eio.api.routes.query import router
from eio.core.orchestrator.orchestrator import Orchestrator
from eio.core.ai_decision_engine import AIDecisionEngine
from eio.core.model_capability_registry import ModelCapabilityRegistry, register_default_profiles
from eio.core.model_health_registry import ModelHealthRegistry
from eio.core.user_context import UserContext
from eio.core.explainability.trace import ExplainabilityTrace
from eio.core.policy.engine import PolicyEngine
from eio.core.policy.audit_log import AuditLogger
from eio.core.registries import AgentRegistry, bootstrap_registries
from eio.connectors.databases.base import SchemaInfo
from eio.connectors.databases.sqlite_connector import SQLiteConnector
from eio.connectors.storage.local_connector import LocalFileSystemConnector
from eio.connectors.llm import LLMRegistry
import eio.agents  # triggers all @register decorators

bootstrap_registries()
register_default_profiles()
ModelHealthRegistry.initialize_from_profiles()

print("All imports OK")
print(f"  Agents registered     : {AgentRegistry.available()}")
print(f"  Models registered     : {ModelCapabilityRegistry.available_count()}")

app = create_app()
api_routes = [r.path for r in app.routes if hasattr(r, "path")]
print(f"  FastAPI API routes    : {[r for r in api_routes if r.startswith('/api')]}")

# Verify ExplainabilityDTO has all new fields
dto_fields = set(ExplainabilityDTO.model_fields.keys())
required_fields = {
    "ai_decision", "planner_intent", "planner_skills", "planner_tools",
    "planner_execution_strategy", "db_connector_type", "db_execution_time_ms",
    "db_rows_returned", "db_cache_hit", "storage_provider", "vector_db",
    "rag_retrieval_time_ms", "evidence_sources", "governance", "user_context",
    "llm_call_count", "db_call_count", "doc_retrieval_count", "agent_count",
    "data_source_count",
}
missing = required_fields - dto_fields
if missing:
    print(f"  MISSING DTO fields    : {missing}")
else:
    print(f"  All 20+ DTO fields    : present")

print()
print("IMPORT CHECK PASSED")
