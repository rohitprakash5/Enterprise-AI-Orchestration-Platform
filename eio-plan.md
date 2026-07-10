# Enterprise Intelligence Orchestrator (EIO) — Implementation Plan

## Top-Level Overview

Build a hackathon-quality enterprise AI orchestration platform (EIO) that coordinates multiple
specialized AI agents, heterogeneous data sources, document repositories, and multiple LLM
providers to answer complex business questions with fully explainable reasoning.

**Tech Stack (MVP)**
| Layer | Technology |
|---|---|
| Backend API | Python 3.11 + FastAPI |
| Orchestration | LangChain / LangGraph |
| UI | Streamlit |
| Primary LLM | OpenAI GPT-4o (via abstraction layer) |
| Vector Store | ChromaDB (local) |
| Demo Database | SQLite |
| Containerization | Docker + Docker Compose |
| Embeddings | OpenAI text-embedding-3-small |
| Document Parsing | PyMuPDF / pdfplumber |

**Core Principles**
- Database-agnostic connector framework
- Storage-agnostic document abstraction layer
- LLM-agnostic provider abstraction
- Policy-driven governance (PII, cost, authorization)
- Every response includes a full explainability trace

**Demo Scenario**: Financial analytics — natural language revenue questions answered by
combining SQL queries against a SQLite financial database with RAG over a PDF annual report.

---

## Sub-Task 1 — Project Scaffold & Repository Structure

**Status**: [ ] pending

### Intent
Establish the full project directory layout, Python packaging configuration, Docker files,
and environment configuration before any feature code is written. Every subsequent sub-task
depends on this scaffold being in place.

### Expected Outcomes
- `eio/` Python package exists with all sub-package directories created
- `requirements.txt` and `pyproject.toml` are present and installable
- `docker-compose.yml` launches backend + Streamlit UI
- `.env.example` documents every required environment variable
- `README.md` describes the project, setup, and demo run instructions

### Todo List
1. Create root directory layout:
   ```
   eio/
     agents/
     connectors/
       databases/
       storage/
       llm/
     core/
       orchestrator/
       policy/
       explainability/
     api/
     ui/
     data/
       demo/
   tests/
   docker/
   ```
2. Create `pyproject.toml` with package metadata and tool config (ruff, pytest)
3. Create `requirements.txt` with pinned versions for: fastapi, uvicorn, langchain,
   langchain-openai, langchain-community, chromadb, sqlalchemy, pdfplumber, streamlit,
   python-dotenv, pydantic, openai
4. Create `docker-compose.yml` with services: `eio-api` (FastAPI) and `eio-ui` (Streamlit)
5. Create `Dockerfile` for the API service and one for the UI service
6. Create `.env.example` listing: `OPENAI_API_KEY`, `EIO_ACTIVE_LLM`, `EIO_ACTIVE_DB`,
   `EIO_ACTIVE_STORAGE`, `EIO_POLICY_COST_LIMIT_USD`, `EIO_LOG_LEVEL`
7. Create `README.md` with project overview, quickstart, and demo scenario description
8. Create `eio/__init__.py` and `__init__.py` files for every sub-package

### Relevant Context
- Greenfield project, no existing code
- All subsequent sub-tasks place files inside the `eio/` package

---

## Sub-Task 2 — Database Connector Abstraction Layer

**Status**: [ ] pending

### Intent
Define a `DatabaseConnector` abstract base class that all database drivers must implement,
then build a concrete `SQLiteConnector` for the demo. A `ConnectorRegistry` maps string
identifiers to connector classes so the active connector is selected purely by configuration.

### Expected Outcomes
- `eio/connectors/databases/base.py` — `DatabaseConnector` ABC with `connect()`,
  `execute_query(sql)`, `get_schema()`, `close()`, and `health_check()` methods
- `eio/connectors/databases/sqlite_connector.py` — concrete SQLite implementation
- `eio/connectors/databases/registry.py` — `ConnectorRegistry` with `register()` and
  `get_connector(name)` factory
- `eio/connectors/databases/stubs/` — stub files for PostgreSQL, SQL Server, Snowflake,
  Oracle, MySQL, DuckDB, Databricks, DB2 (raise `NotImplementedError` with instructions)
- Unit tests in `tests/connectors/test_database_connectors.py` pass against the SQLite impl
- Switching from SQLite to any other connector requires only an env-var change

### Todo List
1. Define `DatabaseConnector` ABC in `base.py` with typed method signatures using Pydantic
   models for `QueryResult` (columns, rows, row_count, execution_time_ms)
2. Implement `SQLiteConnector` using SQLAlchemy Core (not ORM) so the same pattern works
   for all SQL databases; read connection string from env/config
3. Implement `ConnectorRegistry` as a singleton with auto-registration via a `@register`
   decorator pattern
4. Create stub connector files for all other listed databases — each stub imports `base.py`
   and raises `NotImplementedError("Install <driver> and set EIO_ACTIVE_DB=<name>")` for
   each method. Include the pip install command in the error message.
5. Register all connectors in `eio/connectors/databases/__init__.py`
6. Write unit tests covering: connect, execute_query, get_schema, health_check on SQLite

### Relevant Context
- Use SQLAlchemy `text()` for raw SQL execution so the pattern is consistent across engines
- `QueryResult` is consumed by the `DatabaseExecutionAgent` in Sub-Task 5

---

## Sub-Task 3 — Storage Connector Abstraction Layer

**Status**: [ ] pending

### Intent
Define a `StorageConnector` abstract base class for document repositories and implement a
`LocalFileSystemConnector` for the demo. Pattern mirrors the database connector layer.

### Expected Outcomes
- `eio/connectors/storage/base.py` — `StorageConnector` ABC with `list_documents()`,
  `read_document(path)`, `write_document(path, content)`, and `health_check()` methods
- `eio/connectors/storage/local_connector.py` — reads from a configurable local directory
- `eio/connectors/storage/registry.py` — `StorageRegistry` with same `@register` pattern
- Stub files for: S3, Azure Blob, GCS, IBM COS, SharePoint, OneDrive
- Unit tests covering list and read operations on the local connector

### Todo List
1. Define `StorageConnector` ABC in `base.py`; define `DocumentMetadata` Pydantic model
   (name, path, size_bytes, content_type, last_modified)
2. Implement `LocalFileSystemConnector` — `list_documents()` returns `DocumentMetadata` for
   each file in the configured root directory; `read_document()` returns raw bytes
3. Implement `StorageRegistry` mirroring the database registry pattern
4. Create stub connector files for all other listed storage providers
5. Register all connectors in `eio/connectors/storage/__init__.py`
6. Write unit tests using a temporary directory fixture

### Relevant Context
- `read_document()` returns raw bytes so the `DocumentRetrievalAgent` can handle any MIME type
- The `RAGAgent` will call `StorageConnector.list_documents()` on startup to build the index

---

## Sub-Task 4 — LLM Provider Abstraction Layer & Intelligent Model Router

**Status**: [ ] pending

### Intent
Define a `LLMProvider` abstract base class, implement the `OpenAIProvider` for the MVP, and
build a `ModelRouter` that selects the optimal provider/model combination based on a
`RoutingContext` (complexity, SQL needed, RAG needed, token estimate, policy constraints).

### Expected Outcomes
- `eio/connectors/llm/base.py` — `LLMProvider` ABC with `complete(prompt, context)` and
  `embed(text)` methods; `LLMResponse` Pydantic model includes model name, token usage,
  cost estimate, and latency
- `eio/connectors/llm/openai_provider.py` — OpenAI GPT-4o implementation
- Stub providers for: IBM Granite, Anthropic Claude, Gemini, Ollama
- `eio/connectors/llm/router.py` — `ModelRouter` with `select_model(routing_context)` method
  that returns `RoutingDecision` (provider, model, reason, estimated_cost)
- `ModelRouter` applies policy constraints from the `PolicyEngine` (Sub-Task 7)
- Unit tests covering routing logic under different complexity/policy combinations

### Todo List
1. Define `LLMProvider` ABC; define `LLMRequest`, `LLMResponse`, `RoutingContext`,
   `RoutingDecision` as Pydantic models in `base.py`
2. Implement `OpenAIProvider` using the `openai` Python SDK directly (not via LangChain
   wrapper) so the abstraction is clean; support both chat completion and embedding calls
3. Create stub provider files for all other listed LLMs
4. Implement `ModelRouter.select_model()` using a decision tree:
   - If `routing_context.estimated_tokens > policy.token_budget` → reject with explanation
   - If `routing_context.complexity == "low"` and no SQL → route to cheaper/local model
   - If SQL generation needed → prefer GPT-4o or equivalent high-accuracy model
   - If RAG needed → prefer model with large context window
   - Always log routing decision into the explainability trace
5. Register all providers in `eio/connectors/llm/__init__.py`
6. Write unit tests for routing decisions under multiple scenarios

### Relevant Context
- `RoutingContext` is populated by the `PlannerAgent` in Sub-Task 5
- `RoutingDecision` is stored in `ExplainabilityTrace` (Sub-Task 6)
- Cost estimates use a per-token rate table stored in `eio/core/llm_pricing.py`

---

## Sub-Task 5 — Multi-Agent Framework & All Agent Implementations

**Status**: [ ] pending

### Intent
Implement all thirteen specialized agents as discrete, independently callable Python classes
with a shared `BaseAgent` interface. Wire them together in a LangGraph-powered orchestrator
that builds a dynamic execution DAG per request.

### Expected Outcomes
- `eio/agents/base.py` — `BaseAgent` ABC with `run(context: AgentContext) -> AgentResult`
- All 13 agents implemented in `eio/agents/`:
  - `planner_agent.py` — intent classification, complexity scoring, tool selection, routing
  - `metadata_discovery_agent.py` — schema introspection, table/column discovery
  - `semantic_schema_agent.py` — maps business terms to schema columns using a glossary
  - `sql_generation_agent.py` — generates SQL from natural language + schema context
  - `sql_validation_agent.py` — validates SQL syntax and safety before execution
  - `database_execution_agent.py` — executes validated SQL via the DB connector
  - `document_retrieval_agent.py` — fetches candidate documents from storage connector
  - `rag_agent.py` — chunks documents, embeds, queries ChromaDB, returns top-k passages
  - `business_glossary_agent.py` — resolves business term definitions
  - `data_quality_agent.py` — flags nulls, outliers, data freshness issues in results
  - `lineage_agent.py` — records what data was read from where
  - `migration_reconciliation_agent.py` — compares query results across sources
  - `response_synthesis_agent.py` — combines all evidence into a final natural language answer
- `eio/core/orchestrator/orchestrator.py` — LangGraph DAG that routes control flow between agents
- `eio/data/demo/` — SQLite demo DB (`financial.db`) with seed data + sample PDF annual report

### Todo List
1. Create `BaseAgent` ABC in `base.py`; define `AgentContext` (shared state bag passed
   between agents) and `AgentResult` (output, metadata, execution_time_ms) as Pydantic models
2. Implement `PlannerAgent`: accepts raw user query, calls LLM to classify intent,
   estimate complexity (low/medium/high), detect required tools, populate `RoutingContext`,
   return `PlannerResult` including `selected_agents` list and `routing_context`
3. Implement `MetadataDiscoveryAgent`: calls `DatabaseConnector.get_schema()`, formats
   schema as a structured context string for downstream agents
4. Implement `SemanticSchemaAgent`: loads a `business_glossary.json` file mapping terms
   like "revenue" → `transactions.amount WHERE type='revenue'`; enriches schema context
5. Implement `SQLGenerationAgent`: builds a prompt with schema context + business term
   mappings + user question, calls LLM to generate SQL, returns raw SQL string
6. Implement `SQLValidationAgent`: parses generated SQL with `sqlparse`; checks for
   dangerous keywords (DROP, DELETE, UPDATE, INSERT, TRUNCATE); returns validated SQL or error
7. Implement `DatabaseExecutionAgent`: calls `DatabaseConnector.execute_query()`, returns
   `QueryResult`; records lineage entry
8. Implement `DocumentRetrievalAgent`: calls `StorageConnector.list_documents()`, filters
   by relevance to query keywords, returns candidate document paths
9. Implement `RAGAgent`: on first call, loads + chunks all PDFs, embeds and upserts into
   ChromaDB; on query, embeds user question, queries collection for top-5 chunks, returns
   passages with source metadata
10. Implement `BusinessGlossaryAgent`: returns definition for business terms detected in
    the query; used for explainability annotations
11. Implement `DataQualityAgent`: inspects `QueryResult` rows for nulls, zero values, and
    row count anomalies; returns a quality report
12. Implement `LineageAgent`: accumulates a lineage ledger (which tables/documents were
    accessed) throughout the request lifecycle
13. Implement `MigrationReconciliationAgent`: stub with clear interface for comparing
    results across two database sources (useful for migration validation demos)
14. Implement `ResponseSynthesisAgent`: combines SQL results + RAG passages + glossary
    definitions into a final LLM prompt; returns the natural language answer and confidence score
15. Implement `Orchestrator` using LangGraph: nodes = agents, edges = conditional routing
    based on `PlannerResult.selected_agents`; supports dynamic DAG construction per request
16. Create demo SQLite database with tables: `companies`, `revenue`, `expenses`,
    `quarterly_results`; seed with 3 years of realistic financial data
17. Add a sample PDF (`annual_report_2023.pdf`) to `eio/data/demo/` for RAG demonstration
18. Write integration tests that run a full end-to-end financial query through the orchestrator

### Relevant Context
- `AgentContext` is the central shared state object — all agents read from and write to it
- LangGraph nodes are stateless functions that accept and return `AgentContext`
- `SQLValidationAgent` must ALWAYS run before `DatabaseExecutionAgent`
- ChromaDB collection is initialized at API startup in `eio/api/startup.py`

---

## Sub-Task 6 — Explainability Engine

**Status**: [ ] pending

### Intent
Capture a complete, structured trace of every request: which agents ran, which tools were
called, which models were used, what decisions were made, and the final confidence score.
Expose this trace in both API responses and the Streamlit UI.

### Expected Outcomes
- `eio/core/explainability/trace.py` — `ExplainabilityTrace` Pydantic model with:
  - `request_id` (UUID)
  - `user_query` string
  - `agent_timeline` list of `AgentStep` (agent name, start/end time, input summary, output summary)
  - `routing_decision` (`RoutingDecision` from LLM router)
  - `sql_generated` (the actual SQL query, if any)
  - `documents_retrieved` (list of source filenames)
  - `rag_passages` (top-k passages with source and page number)
  - `data_quality_report`
  - `lineage_ledger`
  - `confidence_score` float 0–1
  - `total_cost_usd` float
  - `total_tokens` int
  - `total_latency_ms` int
- Every agent appends its `AgentStep` to the trace as it executes
- API response always includes the full trace under an `explainability` key
- `ExplainabilityTrace` is serializable to JSON

### Todo List
1. Define all Pydantic models in `eio/core/explainability/trace.py`
2. Add `trace: ExplainabilityTrace` field to `AgentContext` so all agents can append to it
3. Implement `trace.add_step()` method in `BaseAgent` so each agent automatically logs its
   execution step without boilerplate in concrete agent code
4. Implement `trace.finalize()` which computes `total_latency_ms`, `total_tokens`,
   `total_cost_usd`, and `confidence_score` from all accumulated steps
5. Write unit tests verifying that a simulated multi-agent run produces a fully populated trace

### Relevant Context
- `confidence_score` is computed as: `1.0 - (weighted average of data quality flags)`
- The Streamlit UI renders `agent_timeline` as a visual step-by-step breakdown (Sub-Task 8)

---

## Sub-Task 7 — Policy Engine & Governance Layer

**Status**: [ ] pending

### Intent
Implement a `PolicyEngine` that enforces enterprise governance rules before, during, and
after every request. Policies are loaded from a YAML configuration file so they can be
changed without touching code.

### Expected Outcomes
- `eio/core/policy/engine.py` — `PolicyEngine` class with `evaluate(context) -> PolicyResult`
- `eio/core/policy/policies.yaml` — default policy configuration including:
  - `max_cost_usd_per_request: 0.50`
  - `max_tokens_per_request: 16000`
  - `blocked_sql_keywords: [DROP, DELETE, UPDATE, INSERT, TRUNCATE]`
  - `pii_detection_enabled: true`
  - `pii_fields: [ssn, credit_card, email, phone]`
  - `approved_models: [gpt-4o, gpt-3.5-turbo, granite-13b]`
  - `audit_log_enabled: true`
- `eio/core/policy/audit_log.py` — append-only JSON Lines audit log writer
- `PolicyResult` Pydantic model: `allowed: bool`, `violations: list[str]`, `warnings: list[str]`
- `PolicyEngine.evaluate()` is called by the Orchestrator at three checkpoints:
  1. Before routing (token budget, model approval)
  2. Before SQL execution (blocked keyword check)
  3. After response synthesis (PII scan on output)
- Unit tests covering each policy check type

### Todo List
1. Define `PolicyResult` and `PolicyViolation` Pydantic models
2. Implement `PolicyEngine` that loads `policies.yaml` on init using `pyyaml`
3. Implement pre-routing check: validate estimated token count and model name against policy
4. Implement pre-execution SQL check: scan for blocked keywords
5. Implement post-synthesis PII scan: regex-based scan for SSN, credit card, email patterns;
   mask detected PII in the response with `[REDACTED]`
6. Implement `AuditLogger` that writes a JSON Lines entry per request to
   `eio/data/audit/audit.log`; entry includes: timestamp, user_id, query, model used,
   cost, policy violations
7. Wire `PolicyEngine.evaluate()` into the `Orchestrator` at the three checkpoints
8. Write unit tests for all policy checks

### Relevant Context
- `policies.yaml` path is configurable via `EIO_POLICY_CONFIG` env var so it can be
  mounted as a Kubernetes ConfigMap in production
- PII masking must happen BEFORE the response is returned to the Streamlit UI

---

## Sub-Task 8 — FastAPI REST Layer

**Status**: [ ] pending

### Intent
Expose the orchestrator as a clean REST API with OpenAPI docs, health checks, and structured
request/response contracts. This layer is the integration point between the Streamlit UI and
the backend orchestration engine.

### Expected Outcomes
- `eio/api/main.py` — FastAPI app with CORS, lifespan, and router registration
- `eio/api/routes/query.py` — `POST /api/v1/query` endpoint
- `eio/api/routes/health.py` — `GET /api/v1/health` and `GET /api/v1/health/connectors`
- `eio/api/routes/config.py` — `GET /api/v1/config` returns active connectors and models
- `eio/api/schemas.py` — `QueryRequest` and `QueryResponse` Pydantic models
- `QueryResponse` includes: `answer`, `explainability` (full trace), `sql_query`,
  `data_results`, `rag_passages`, `policy_result`, `request_id`
- FastAPI auto-generates Swagger UI at `/docs`
- API starts ChromaDB and warms up the RAG index on lifespan startup

### Todo List
1. Define `QueryRequest` (user_query: str, user_id: str, session_id: str) and
   `QueryResponse` in `eio/api/schemas.py`
2. Implement `POST /api/v1/query` in `routes/query.py`: validate request, instantiate
   `AgentContext`, call `Orchestrator.run()`, return `QueryResponse`
3. Implement `GET /api/v1/health`: returns `{"status": "healthy", "version": "0.1.0"}`
4. Implement `GET /api/v1/health/connectors`: calls `health_check()` on the active DB
   connector and storage connector; returns per-connector status
5. Implement `GET /api/v1/config`: returns active LLM provider, active DB connector name,
   active storage connector name, and policy summary
6. Add a lifespan context manager that initializes ChromaDB collection and seeds demo data
   if it does not exist
7. Add CORS middleware permitting `http://localhost:8501` (Streamlit default port)
8. Write API integration tests using FastAPI's `TestClient`

### Relevant Context
- `Orchestrator.run()` returns `(answer, explainability_trace, policy_result)`
- All routes are prefixed with `/api/v1` for versioning

---

## Sub-Task 9 — Streamlit UI

**Status**: [ ] pending

### Intent
Build a single-page Streamlit application that provides a clean enterprise-grade interface:
a query panel, a structured response panel, and a full explainability sidebar showing the
agent execution timeline, model routing decision, SQL query, RAG passages, cost, and policy
audit results.

### Expected Outcomes
- `eio/ui/app.py` — Streamlit application entry point
- Query input panel with a text area and a "Run Query" button
- Response panel showing: natural language answer, formatted data table (if SQL results),
  and RAG evidence passages with source citations
- Expandable explainability sidebar showing:
  - Agent timeline (step-by-step with timing badges)
  - Model routing decision with explanation
  - SQL query with syntax highlighting
  - Documents retrieved
  - Confidence score as a progress bar
  - Token usage and cost breakdown
  - Policy audit results
- Sample questions panel with pre-loaded financial demo queries
- EIO branding header

### Todo List
1. Create `eio/ui/app.py` with Streamlit page config (wide layout, "EIO" title)
2. Build the header component: EIO logo text, tagline, active connectors status badges
3. Build the query input panel: multi-line text area + submit button + sample questions as
   clickable buttons that auto-populate the query field
4. On submit: call `POST /api/v1/query` via `requests` library with a loading spinner
5. Build the response panel: display `answer` in a styled text block; if `data_results` is
   present, render as `st.dataframe()`; display RAG passages in `st.expander()` blocks
6. Build the explainability sidebar using `st.sidebar`:
   - Agent timeline as a vertical list with icons and timing info
   - Routing decision card showing selected model and reason
   - SQL code block using `st.code(sql, language="sql")`
   - Confidence score using `st.progress()`
   - Token/cost metrics using `st.metric()`
   - Policy result with color-coded pass/warn/fail badges
7. Add sample demo queries: "What was total revenue in Q4 2023?", "Compare revenue vs
   expenses by quarter", "What does the annual report say about growth strategy?"
8. Wire the UI to `http://localhost:8000` (API base URL configurable via env var)

### Relevant Context
- The Streamlit app is a standalone Python script — it does NOT import from `eio/` directly;
  it communicates only via HTTP to keep the architecture clean
- `st.session_state` is used to preserve query history across reruns

---

## Sub-Task 10 — Demo Data, Docker Compose & End-to-End Validation

**Status**: [ ] pending

### Intent
Create all demo seed data, finalize Docker Compose wiring, and validate that the complete
system runs end-to-end from `docker compose up` to a real financial analytics answer with a
full explainability trace visible in the Streamlit UI.

### Expected Outcomes
- `eio/data/demo/seed_financial_db.py` — creates and seeds `financial.db` with realistic data
- `eio/data/demo/annual_report_2023.pdf` — sample PDF annual report (can be a generated one)
- `eio/data/demo/business_glossary.json` — maps 10+ business terms to schema definitions
- `docker-compose.yml` correctly maps ports, volumes, and env files for both services
- Running `docker compose up` brings up both services within 60 seconds
- A demo query "What was total revenue in Q4 2023 and what growth does the annual report project?" produces:
  - A correct SQL-derived revenue figure
  - A RAG-sourced growth projection from the PDF
  - A synthesized natural language answer combining both
  - A full explainability trace in the UI

### Todo List
1. Write `seed_financial_db.py`: create tables `companies`, `revenue`, `expenses`,
   `quarterly_results`; insert 3 years of quarterly data for 3 fictional companies
2. Create `business_glossary.json` mapping terms: revenue, expenses, EBITDA, gross margin,
   net income, operating profit, headcount, YoY growth, QoQ growth, run rate
3. Generate or source a sample PDF annual report and place it in `eio/data/demo/`
4. Finalize `docker-compose.yml`:
   - `eio-api`: build from `./docker/api/Dockerfile`, port 8000:8000, mounts `eio/data`
     volume, reads from `.env`
   - `eio-ui`: build from `./docker/ui/Dockerfile`, port 8501:8501, reads `EIO_API_URL`
     env var, depends on `eio-api`
5. Add a `docker/api/Dockerfile` that installs requirements and runs `uvicorn`
6. Add a `docker/ui/Dockerfile` that installs requirements and runs `streamlit run`
7. Run the full demo query manually and confirm correct output with explainability trace
8. Update `README.md` with final setup and demo instructions including sample queries

### Relevant Context
- Demo data must be deterministic and reproducible (fixed seed for random data generation)
- The PDF can be a minimal synthetic one generated with `reportlab` if no real PDF is available
- API startup lifespan handler in Sub-Task 8 will auto-seed the DB if `financial.db` is missing

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit UI (Port 8501)                      │
│  Query Panel │ Response Panel │ Explainability Sidebar           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP POST /api/v1/query
┌─────────────────────────▼───────────────────────────────────────┐
│                   FastAPI REST Layer (Port 8000)                  │
│         /query  /health  /health/connectors  /config             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    Orchestrator (LangGraph DAG)                   │
│                                                                   │
│  ┌──────────────┐    ┌───────────────────┐   ┌───────────────┐  │
│  │ PlannerAgent │───▶│ MetadataDiscovery │──▶│ SemanticSchema│  │
│  └──────────────┘    └───────────────────┘   └───────┬───────┘  │
│                                                       │           │
│  ┌──────────────┐    ┌───────────────────┐   ┌───────▼───────┐  │
│  │ SQLValidation│◀───│  SQLGeneration    │◀──│  (schema ctx) │  │
│  └──────┬───────┘    └───────────────────┘   └───────────────┘  │
│         │                                                         │
│  ┌──────▼───────┐    ┌───────────────────┐   ┌───────────────┐  │
│  │  DB Execution│    │ DocumentRetrieval │──▶│   RAG Agent   │  │
│  └──────┬───────┘    └───────────────────┘   └───────┬───────┘  │
│         │                                             │           │
│  ┌──────▼─────────────────────────────────────────────▼───────┐  │
│  │              Response Synthesis Agent                        │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                     │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │  Explainability Trace + Policy Engine Audit                 │  │
│  └─────────────────────────────────────────────────────────── ┘  │
└─────────────────────────────────────────────────────────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼──────────────┐
│ DB Connector Layer  │   │ Storage Connector Layer  │
│  SQLite (demo)      │   │  LocalFileSystem (demo)  │
│  PostgreSQL (stub)  │   │  S3 (stub)               │
│  Snowflake (stub)   │   │  Azure Blob (stub)        │
│  ...                │   │  ...                      │
└─────────────────────┘   └──────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────┐
│             LLM Provider Abstraction Layer           │
│  OpenAI GPT-4o (active) │ Model Router              │
│  IBM Granite (stub)     │ PolicyEngine              │
│  Anthropic (stub)       │ CostTracker               │
└─────────────────────────────────────────────────────┘
```

### LLM Routing Decision Tree

```
User Query
    │
    ▼
PlannerAgent estimates:
  - complexity: low / medium / high
  - sql_needed: bool
  - rag_needed: bool
  - estimated_tokens: int
    │
    ▼
PolicyEngine pre-check:
  - token_budget exceeded? → REJECT
  - model approved? → REJECT if not in approved list
    │
    ▼
ModelRouter.select_model():
  IF complexity == "low" AND NOT sql_needed AND NOT rag_needed
      → route to gpt-3.5-turbo (cost optimized)
  ELSE IF sql_needed
      → route to gpt-4o (accuracy critical)
  ELSE IF rag_needed AND estimated_tokens > 8000
      → route to gpt-4o (large context)
  ELSE
      → route to gpt-4o (default premium)
    │
    ▼
RoutingDecision logged to ExplainabilityTrace
```

---

## File Structure Reference

```
Enterprise-AI-Orchestration-Platform/
├── eio/
│   ├── agents/
│   │   ├── base.py
│   │   ├── planner_agent.py
│   │   ├── metadata_discovery_agent.py
│   │   ├── semantic_schema_agent.py
│   │   ├── sql_generation_agent.py
│   │   ├── sql_validation_agent.py
│   │   ├── database_execution_agent.py
│   │   ├── document_retrieval_agent.py
│   │   ├── rag_agent.py
│   │   ├── business_glossary_agent.py
│   │   ├── data_quality_agent.py
│   │   ├── lineage_agent.py
│   │   ├── migration_reconciliation_agent.py
│   │   └── response_synthesis_agent.py
│   ├── connectors/
│   │   ├── databases/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── sqlite_connector.py
│   │   │   └── stubs/  (postgres, sqlserver, snowflake, oracle, mysql, duckdb, databricks, db2)
│   │   ├── storage/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── local_connector.py
│   │   │   └── stubs/  (s3, azure_blob, gcs, ibm_cos, sharepoint, onedrive)
│   │   └── llm/
│   │       ├── base.py
│   │       ├── registry.py
│   │       ├── router.py
│   │       ├── openai_provider.py
│   │       └── stubs/  (granite, claude, gemini, ollama)
│   ├── core/
│   │   ├── orchestrator/
│   │   │   └── orchestrator.py
│   │   ├── policy/
│   │   │   ├── engine.py
│   │   │   ├── audit_log.py
│   │   │   └── policies.yaml
│   │   ├── explainability/
│   │   │   └── trace.py
│   │   └── llm_pricing.py
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── query.py
│   │       ├── health.py
│   │       └── config.py
│   ├── ui/
│   │   └── app.py
│   └── data/
│       ├── demo/
│       │   ├── seed_financial_db.py
│       │   ├── financial.db  (generated)
│       │   ├── annual_report_2023.pdf
│       │   └── business_glossary.json
│       └── audit/
│           └── audit.log  (generated)
├── tests/
│   ├── connectors/
│   ├── agents/
│   ├── core/
│   └── api/
├── docker/
│   ├── api/Dockerfile
│   └── ui/Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```
