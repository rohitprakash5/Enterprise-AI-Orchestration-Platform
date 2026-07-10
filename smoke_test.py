"""
EIO Smoke Test
===============
Run with: python smoke_test.py
"""
import sys, os

sys.path.insert(0, ".")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from dotenv import load_dotenv
load_dotenv()

import chromadb
from eio.connectors.databases import ConnectorRegistry as DBRegistry
from eio.connectors.llm import LLMRegistry
from eio.connectors.storage import StorageRegistry
from eio.core.orchestrator.orchestrator import Orchestrator

# ── Build connectors the same way main.py does ─────────────────────────────
db = DBRegistry.get("sqlite", db_path="eio/data/demo/financial.db")
db.connect()

storage = StorageRegistry.get("local", root_path="eio/data/demo/documents")

active_llm  = os.getenv("EIO_ACTIVE_LLM", "mock")
openai_key  = os.getenv("OPENAI_API_KEY", "").strip()
hf_token    = os.getenv("HF_TOKEN", "").strip()

if active_llm == "openai" and openai_key:
    llm = LLMRegistry.get("openai", api_key=openai_key)
elif active_llm == "gpt_oss" and hf_token:
    llm = LLMRegistry.get("gpt_oss", hf_token=hf_token,
                           model_id=os.getenv("EIO_GPTOSS_MODEL_ID", "openai/gpt-oss-20b"))
else:
    llm = LLMRegistry.get("mock")

print(f"LLM provider : {llm.provider_name}/{llm.default_model}")

chroma  = chromadb.PersistentClient(path="eio/data/chroma")
coll    = chroma.get_or_create_collection("eio_documents")
print(f"Chroma chunks: {coll.count()}")

orch = Orchestrator(
    db_connector=db,
    storage_connector=storage,
    llm_provider=llm,
    vector_collection=coll,
)
print("Orchestrator : OK\n")

ctx = orch.run(
    user_query="What was Apex Analytics revenue in Q4 2023?",
    user_id="smoke_test",
)

t = ctx.trace
sep = "=" * 60
print(sep)
print("SMOKE TEST RESULT")
print(sep)
print(f"Answer        : {(ctx.final_answer or '')[:200]}")
print(f"SQL           : {t.sql_generated}")
print(f"SQL validated : {t.sql_validated}")
print(f"Agents run    : {t.agent_count}")
print(f"Timeline      : {[s.agent_name for s in t.agent_timeline]}")
print(f"Tokens        : {t.total_tokens}")
print(f"Cost USD      : {t.total_cost_usd:.6f}")
print(f"Latency ms    : {t.total_latency_ms:.0f}")
print(f"Confidence    : {t.confidence_score}")
print()
ai = t.ai_decision or {}
print(f"AI Decision   : {bool(ai)} | candidates={len(ai.get('candidates_evaluated', []))}")
print(f"  Selected    : {ai.get('selected_display_name','N/A')} (score={ai.get('selection_confidence',0):.1f})")
print(f"  Task routes : {len(ai.get('task_assignments', []))}")
print(f"  Reason      : {ai.get('selection_reason','N/A')[:100]}")
print()
print(f"Planner intent   : {(t.planner_intent or '')[:100]}")
print(f"Planner strategy : {t.planner_execution_strategy}")
print(f"Planner skills   : {t.planner_skills}")
print()
print(f"DB connector     : {t.db_connector_type} | exec={t.db_execution_time_ms:.1f}ms | rows={t.db_rows_returned}")
print(f"Storage provider : {t.storage_provider} | vector={t.vector_db} | rag={t.rag_retrieval_time_ms:.1f}ms")
print()
print(f"Governance keys  : {list(t.governance.keys())}")
print(f"User context     : {list(t.user_context.keys())}")
print(f"Evidence sources : {t.evidence_sources}")
print()
print(f"LLM calls / DB calls / Doc calls : {t.llm_call_count} / {t.db_call_count} / {t.doc_retrieval_count}")
print(f"Data sources     : {t.data_source_count}")
print()
print(f"Policy violations: {t.policy_violations}")
print(f"Policy warnings  : {t.policy_warnings}")
print()
print(sep)
print("SMOKE TEST PASSED")
print(sep)
