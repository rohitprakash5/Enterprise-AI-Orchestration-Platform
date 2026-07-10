# Enterprise Intelligence Orchestrator (EIO)

> **A production-quality, multi-agent AI orchestration platform** that coordinates specialized AI agents, heterogeneous enterprise data sources, document repositories, and multiple LLM providers to answer complex business questions with fully explainable reasoning.

EIO is **not a chatbot**. It is an enterprise AI orchestration platform built on three core abstractions:

- **Database-agnostic connector framework** (SQLite → PostgreSQL → Snowflake → DB2 via config only)
- **Storage-agnostic document layer** (local → S3 → Azure Blob → SharePoint via config only)
- **LLM-agnostic provider abstraction** (OpenAI → Anthropic → IBM Granite → Ollama via config only)

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PlannerAgent (Intent + Plan)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ RoutingContext
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              CapabilityRegistry → ToolRegistry → AgentRegistry  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ selected_agents[]
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ModelRouter + PolicyEngine                    │
│         (complexity + governance + cost → model selection)      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ RoutingDecision
                           ▼
┌────────────────────── Dynamic Agent DAG ────────────────────────┐
│                                                                  │
│  MetadataDiscovery → SemanticSchema → SQLGeneration             │
│       → SQLValidation → DatabaseExecution                       │
│                                                                  │
│  DocumentRetrieval → RAGAgent                                   │
│                                                                  │
│  DataQuality · Lineage · BusinessGlossary                       │
│                                                                  │
│  ResponseSynthesis (combines ALL evidence)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│       ExplainabilityTrace + PolicyEngine (PII scan) + Audit     │
└─────────────────────────────────────────────────────────────────┘
```

### Connector Architecture

```
DatabaseConnector (ABC)
├── SQLiteConnector          ← MVP demo
├── PostgreSQLConnector      ← stub (extend)
├── SnowflakeConnector       ← stub (extend)
├── SQLServerConnector       ← stub (extend)
├── OracleConnector          ← stub (extend)
├── MySQLConnector           ← stub (extend)
├── DuckDBConnector          ← stub (extend)
├── DatabricksConnector      ← stub (extend)
└── DB2Connector             ← stub (extend)

StorageConnector (ABC)
├── LocalFileSystemConnector ← MVP demo
├── S3Connector              ← stub (extend)
├── AzureBlobConnector       ← stub (extend)
├── GCSConnector             ← stub (extend)
├── IBMCOSConnector          ← stub (extend)
├── SharePointConnector      ← stub (extend)
└── OneDriveConnector        ← stub (extend)

LLMProvider (ABC)
├── OpenAIProvider           ← MVP demo (GPT-4o)
├── AnthropicProvider        ← stub (extend)
├── GraniteProvider          ← stub (extend)
├── GeminiProvider           ← stub (extend)
└── OllamaProvider           ← stub (extend)
```

---

## Quick Start

### Option 1: Local Python

```bash
# 1. Clone and install
git clone <repo>
cd Enterprise-AI-Orchestration-Platform
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# 3. Generate demo data
python eio/data/demo/seed_financial_db.py
python eio/data/demo/generate_annual_report.py

# 4. Start the API
uvicorn eio.api.main:app --reload --port 8000

# 5. Start the UI (new terminal)
streamlit run eio/ui/app.py --server.port 8501
```

Open http://localhost:8501

### Option 2: Docker Compose

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

docker compose up --build
```

Open http://localhost:8501

---

## Demo Scenario: Financial Analytics

The MVP demo is pre-loaded with:

**Database (SQLite)**: 3 years of quarterly financial data for 3 fictional companies
- Tables: `companies`, `revenue`, `expenses`, `quarterly_results`
- 2021-2023, all 4 quarters, multi-product-line revenue breakdown

**Documents (Local PDF)**: Apex Analytics Corp Annual Report 2023
- CEO letter, financial highlights, quarterly breakdown, growth strategy, risk factors
- RAG-indexed via ChromaDB with OpenAI embeddings

**Business Glossary**: 13 financial terms mapped to SQL patterns
- revenue, expenses, EBITDA, gross margin, YoY growth, QoQ growth, run rate, etc.

### Try These Queries

| Query | Agents Activated |
|---|---|
| "What was total revenue for Apex in Q4 2023?" | Planner, MetadataDiscovery, SemanticSchema, SQLGen, SQLValidation, DBExec, DataQuality, ResponseSynthesis |
| "Compare revenue vs expenses by quarter in 2023" | Full SQL pipeline + DataQuality |
| "What does the annual report say about growth strategy?" | Planner, DocRetrieval, RAG, ResponseSynthesis |
| "What was Q4 2023 revenue and what growth does the report project?" | Full pipeline: SQL + RAG combined |
| "Which company had highest YoY growth in 2022?" | Planner, MetadataDiscovery, SQLGen → DBExec |

---

## Adding a New Agent

EIO is designed for zero-friction extensibility:

```python
# eio/agents/my_new_agent.py
from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

@AgentRegistry.register("my_new_agent")   # ← single decorator
class MyNewAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "my_new_agent"

    def run(self, context: AgentContext) -> AgentResult:
        # Access: context.user_query, context.db_connector,
        #         context.llm_provider, context.sql_result, etc.
        result = do_my_work(context)
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=result,
            output_summary="My agent completed successfully",
        )
```

Then import it in `eio/agents/__init__.py`. That's it — no changes to the Orchestrator, API, or UI.

---

## Adding a New Database Connector

```python
# eio/connectors/databases/postgres_connector.py
from eio.connectors.databases.base import DatabaseConnector, QueryResult, SchemaInfo
from eio.connectors.databases.registry import ConnectorRegistry

@ConnectorRegistry.register("postgresql")
class PostgreSQLConnector(DatabaseConnector):
    def __init__(self, url: str) -> None: ...
    def connect(self) -> None: ...
    def execute_query(self, sql: str, ...) -> QueryResult: ...
    def get_schema(self) -> SchemaInfo: ...
    def close(self) -> None: ...
    def health_check(self) -> dict: ...
```

Set `EIO_ACTIVE_DB=postgresql` in `.env`. No other changes needed.

---

## Adding a New LLM Provider

```python
# eio/connectors/llm/granite_provider.py
from eio.connectors.llm.base import LLMProvider, LLMRequest, LLMResponse, EmbeddingResponse
from eio.connectors.llm.registry import LLMRegistry

@LLMRegistry.register("granite")
class GraniteProvider(LLMProvider):
    # implement complete() and embed()
    ...
```

Set `EIO_ACTIVE_LLM=granite` in `.env`. No other changes needed.

---

## Project Structure

```
eio/
├── agents/           ← 13 specialized agents
├── connectors/
│   ├── databases/    ← DatabaseConnector ABC + SQLite + 8 stubs
│   ├── storage/      ← StorageConnector ABC + LocalFS + 6 stubs
│   └── llm/          ← LLMProvider ABC + OpenAI + ModelRouter + 4 stubs
├── core/
│   ├── orchestrator/ ← Dynamic multi-agent execution engine
│   ├── policy/       ← PolicyEngine (YAML-driven) + AuditLogger
│   ├── explainability/ ← ExplainabilityTrace (full request trace)
│   └── registries.py ← CapabilityRegistry + ToolRegistry + AgentRegistry
├── api/              ← FastAPI REST layer
├── ui/               ← Streamlit single-page application
└── data/
    ├── demo/         ← SQLite DB seed, PDF annual report, business glossary
    └── audit/        ← Append-only audit log (JSON Lines)
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/query` | POST | Execute a business query |
| `/api/v1/health` | GET | API health check |
| `/api/v1/health/connectors` | GET | Per-connector health |
| `/api/v1/config` | GET | Active connector configuration |
| `/docs` | GET | Swagger UI |

### Query Request
```json
{
  "user_query": "What was Q4 2023 revenue?",
  "user_id": "user@company.com",
  "session_id": "optional-session-id"
}
```

### Query Response (summary)
```json
{
  "request_id": "uuid",
  "answer": "Apex Analytics generated $58.2M in Q4 2023...",
  "sql_query": "SELECT SUM(amount) FROM revenue WHERE ...",
  "data_results": { "columns": [...], "rows": [...], "row_count": 3 },
  "rag_passages": [{ "text": "...", "source": "annual_report_2023.pdf", "score": 0.91 }],
  "confidence_score": 0.94,
  "total_tokens": 1842,
  "total_cost_usd": 0.0121,
  "total_latency_ms": 3420,
  "explainability": {
    "agent_timeline": [...],
    "routing_decision": { "model": "gpt-4o", "reason": "..." },
    "sql_validated": true,
    "data_quality": { "quality_score": 1.0 },
    "lineage": [...]
  }
}
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (required for MVP) |
| `EIO_ACTIVE_LLM` | `openai` | Active LLM provider |
| `EIO_ACTIVE_DB` | `sqlite` | Active database connector |
| `EIO_ACTIVE_STORAGE` | `local` | Active storage connector |
| `EIO_SQLITE_PATH` | `eio/data/demo/financial.db` | SQLite database path |
| `EIO_LOCAL_STORAGE_PATH` | `eio/data/demo/documents` | Document root directory |
| `EIO_CHROMA_PATH` | `eio/data/chroma` | ChromaDB persistence path |
| `EIO_POLICY_CONFIG` | `eio/core/policy/policies.yaml` | Policy configuration file |
| `EIO_POLICY_COST_LIMIT_USD` | `0.50` | Max cost per request |
| `EIO_POLICY_TOKEN_BUDGET` | `16000` | Max tokens per request |
| `EIO_API_URL` | `http://localhost:8000` | API URL (used by UI) |
| `EIO_LOG_LEVEL` | `INFO` | Logging level |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11, FastAPI, Uvicorn |
| Agent Orchestration | Custom AgentRegistry + LangGraph-ready |
| LLM (MVP) | OpenAI GPT-4o |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB (local persistent) |
| Database (MVP) | SQLite via SQLAlchemy Core |
| Document Parsing | pdfplumber |
| UI | Streamlit |
| Containerization | Docker + Docker Compose |
| Governance | YAML-driven PolicyEngine + JSON Lines audit log |

---

## Roadmap

- [ ] Full implementations of PostgreSQL, Snowflake, DB2 connectors
- [ ] IBM Granite / watsonx.ai provider implementation
- [ ] Anthropic Claude provider implementation
- [ ] Ollama local model provider
- [ ] LangGraph state machine integration for complex DAGs
- [ ] OpenLineage event emission for enterprise data governance
- [ ] Kubernetes Helm chart
- [ ] RBAC and multi-tenant user isolation
- [ ] Real-time streaming responses via SSE
- [ ] Advanced reconciliation with tolerance-based comparison
