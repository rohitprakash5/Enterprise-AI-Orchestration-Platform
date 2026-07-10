"""
Mock LLM Provider
==================
Fully functional LLM provider that requires NO API key.
Returns deterministic, realistic-looking responses based on
keyword analysis of the input prompt.

Used for:
  - Local development without any API key
  - CI/CD pipelines
  - Demo environments
  - Testing the orchestration platform end-to-end

When OPENAI_API_KEY is set, the real OpenAI provider is used instead.
Switch back any time: EIO_ACTIVE_LLM=mock

The mock provider demonstrates that the platform architecture is
completely LLM-agnostic — any compliant provider can be swapped in
via configuration with zero code changes.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from eio.connectors.llm.base import (
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)
from eio.core.registries import AgentRegistry

# ---------------------------------------------------------------------------
# Deterministic embedding (768-dim unit vector derived from text hash)
# ---------------------------------------------------------------------------

def _mock_embedding(text: str, dims: int = 1536) -> list[float]:
    """
    Generate a deterministic pseudo-embedding from text.
    Similar texts produce similar vectors (same keywords → same hash components).
    Sufficient for ChromaDB cosine similarity to return sensible results.
    """
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    rng_state = seed
    vec: list[float] = []
    for _ in range(dims):
        rng_state = (rng_state * 1664525 + 1013904223) & 0xFFFFFFFF
        val = (rng_state / 0xFFFFFFFF) * 2 - 1
        vec.append(val)
    # Normalize to unit vector
    magnitude = sum(v * v for v in vec) ** 0.5
    if magnitude > 0:
        vec = [v / magnitude for v in vec]
    return vec


# ---------------------------------------------------------------------------
# Canned response templates
# ---------------------------------------------------------------------------

_PLANNER_TEMPLATE = """{
  "intent": "financial data query combining structured database results and document evidence",
  "complexity": "high",
  "sql_needed": true,
  "rag_needed": true,
  "schema_discovery_needed": true,
  "glossary_needed": true,
  "data_quality_check": true,
  "multi_source": true,
  "estimated_tokens": 3500,
  "selected_agents": [
    "business_glossary",
    "metadata_discovery",
    "semantic_schema",
    "sql_generation",
    "sql_validation",
    "database_execution",
    "document_retrieval",
    "rag",
    "data_quality",
    "lineage",
    "response_synthesis"
  ],
  "selected_capabilities": ["sql_query", "schema_discovery", "document_retrieval", "rag", "data_quality", "lineage_tracking", "response_synthesis"],
  "selected_tools": ["get_schema", "generate_sql", "validate_sql", "execute_sql", "list_documents", "embed_text", "query_vector_store", "check_data_quality", "record_lineage", "synthesize_response"],
  "reasoning": "The query requires both structured financial data (SQL) and unstructured document evidence (RAG). High complexity warrants a full multi-agent pipeline to deliver an accurate, evidence-based response with complete explainability."
}"""

_SQL_TEMPLATES: dict[str, str] = {
    "revenue":      "SELECT c.name AS company, qr.year, qr.quarter, ROUND(qr.total_revenue, 2) AS total_revenue FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id ORDER BY qr.year DESC, qr.quarter DESC LIMIT 20",
    "q4":           "SELECT c.name AS company, ROUND(qr.total_revenue, 2) AS revenue, ROUND(qr.ebitda, 2) AS ebitda, qr.yoy_growth_pct FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id WHERE qr.quarter = 4 AND qr.year = 2023 ORDER BY revenue DESC",
    "expense":      "SELECT c.name AS company, qr.year, qr.quarter, ROUND(qr.total_expenses, 2) AS total_expenses FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id ORDER BY qr.year DESC, qr.quarter DESC LIMIT 20",
    "growth":       "SELECT c.name AS company, qr.year, qr.quarter, qr.yoy_growth_pct FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id WHERE qr.yoy_growth_pct IS NOT NULL ORDER BY qr.yoy_growth_pct DESC LIMIT 15",
    "ebitda":       "SELECT c.name AS company, qr.year, qr.quarter, ROUND(qr.ebitda, 2) AS ebitda, ROUND(qr.gross_margin, 2) AS gross_margin_pct FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id WHERE qr.year = 2023 ORDER BY ebitda DESC",
    "compare":      "SELECT c.name AS company, qr.year, qr.quarter, ROUND(qr.total_revenue, 2) AS revenue, ROUND(qr.total_expenses, 2) AS expenses, ROUND(qr.gross_profit, 2) AS gross_profit FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id WHERE qr.year = 2023 ORDER BY qr.quarter, revenue DESC",
    "default":      "SELECT c.name AS company, qr.year, qr.quarter, ROUND(qr.total_revenue, 2) AS total_revenue, ROUND(qr.total_expenses, 2) AS total_expenses, ROUND(qr.gross_profit, 2) AS gross_profit, ROUND(qr.ebitda, 2) AS ebitda FROM quarterly_results qr JOIN companies c ON c.id = qr.company_id WHERE qr.year = 2023 ORDER BY qr.quarter, c.name LIMIT 20",
}

_SYNTHESIS_TEMPLATE = """## Analysis: {query}

### Structured Data Findings

Based on the financial database query, here is what the data shows:

{sql_summary}

### Document Evidence

From the Apex Analytics Corp Annual Report 2023:

{doc_summary}

### Synthesized Assessment

The structured financial data and document evidence together provide a consistent picture of **strong enterprise performance**. Apex Analytics Corp leads in revenue growth at approximately **22% YoY**, driven primarily by Cloud Platform expansion (+41% YoY). Nova Financial Systems contributes the highest absolute revenue volumes given its financial services scale, while Crest Manufacturing shows steady industrial growth.

The annual report projects continued momentum with **18–24% revenue growth in 2024**, supported by AI-powered analytics investments and geographic expansion into APAC and EMEA markets. Management has indicated that Q4 typically represents the strongest seasonal quarter, consistent with the 25.7% QoQ acceleration observed in Q4 2023.

### Evidence Sources
- **Database**: `quarterly_results`, `companies`, `revenue` tables — EIO Financial Demo DB (SQLite)
- **Document**: Apex Analytics Corp Annual Report 2023 (PDF, local storage)
- **Agents**: Planner → MetadataDiscovery → SemanticSchema → SQLGeneration → SQLValidation → DBExecution → DocumentRetrieval → RAG → DataQuality → Lineage → ResponseSynthesis
- **Model**: Mock LLM Provider (replace with OpenAI GPT-4o by setting `EIO_ACTIVE_LLM=openai`)

*Note: This response was generated by the EIO Mock LLM Provider for demo purposes. Set `OPENAI_API_KEY` and `EIO_ACTIVE_LLM=openai` in `.env` to enable full AI-powered responses.*
"""


def _pick_sql(prompt: str) -> str:
    """Select the most relevant canned SQL based on prompt keywords."""
    lower = prompt.lower()
    if "q4" in lower or "quarter 4" in lower or "fourth" in lower:
        return _SQL_TEMPLATES["q4"]
    if "growth" in lower or "yoy" in lower or "year over year" in lower:
        return _SQL_TEMPLATES["growth"]
    if "ebitda" in lower or "margin" in lower:
        return _SQL_TEMPLATES["ebitda"]
    if "expense" in lower or "cost" in lower:
        return _SQL_TEMPLATES["expense"]
    if "compar" in lower or "vs " in lower or "versus" in lower:
        return _SQL_TEMPLATES["compare"]
    if "revenue" in lower or "sales" in lower or "income" in lower:
        return _SQL_TEMPLATES["revenue"]
    return _SQL_TEMPLATES["default"]


def _build_synthesis(prompt: str, schema_present: bool) -> str:
    sql_summary = (
        "The financial database returned quarterly results across all three companies "
        "(Apex Analytics Corp, Nova Financial Systems, Crest Manufacturing Ltd) for 2021–2023. "
        "Q4 2023 showed the strongest performance: Apex $58.3M (+22% YoY), "
        "Nova $132.0M, Crest $62.9M."
    ) if schema_present else "No structured data was available for this query."

    doc_summary = (
        'The annual report states: *"2023 was a transformational year... record revenues of '
        '$185.4 million, representing 22% year-over-year growth."* The report projects '
        '2024 revenue of **$218M–$230M (+18%–24% YoY)** and highlights AI-powered analytics '
        'and geographic expansion as primary growth drivers. EBITDA margin reached 38.1% '
        'in 2023 with strong free cash flow of $61.3M.'
    )

    # Extract the core question from the prompt
    query_line = ""
    for line in prompt.split("\n"):
        if "question:" in line.lower() or "query:" in line.lower():
            query_line = line.split(":", 1)[-1].strip()
            break
    if not query_line:
        query_line = "enterprise financial performance"

    return _SYNTHESIS_TEMPLATE.format(
        query=query_line,
        sql_summary=sql_summary,
        doc_summary=doc_summary,
    )


# ---------------------------------------------------------------------------
# Mock LLM Provider class
# ---------------------------------------------------------------------------

class MockLLMProvider(LLMProvider):
    """
    Zero-dependency mock LLM provider.
    Returns deterministic, structurally-correct responses for all agent prompts.
    No API key, no network calls, no cost.

    Register: EIO_ACTIVE_LLM=mock
    """

    _LATENCY_MS = 120   # simulated latency so UI timings look realistic

    def __init__(self, **_kwargs: Any) -> None:
        pass  # no API key needed

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-gpt-demo"

    @property
    def available_models(self) -> list[str]:
        return ["mock-gpt-demo", "mock-gpt-fast"]

    def complete(self, request: LLMRequest) -> LLMResponse:
        time.sleep(self._LATENCY_MS / 1000)

        # Combine all message content for routing
        full_text = " ".join(m.content for m in request.messages)
        if request.system_prompt:
            full_text = request.system_prompt + " " + full_text
        full_lower = full_text.lower()

        # ── Route to the correct canned response ──────────────────────
        content = self._route_response(full_lower, full_text)

        # Approximate token count
        input_tokens = len(full_text.split()) * 2
        output_tokens = len(content.split()) * 2

        return LLMResponse(
            content=content,
            model=self.default_model,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=0.0,
            latency_ms=float(self._LATENCY_MS),
            finish_reason="stop",
        )

    def _route_response(self, lower: str, original: str) -> str:
        # ── 1. Planner: must match first (very distinctive JSON output) ───────
        if "plan the execution" in lower or '"intent"' in lower or "selected_agents" in lower:
            return _PLANNER_TEMPLATE

        # ── 2. Response synthesis: check BEFORE SQL to avoid misrouting ──────
        #    The synthesis prompt contains "SQL Query Results" and "evidence"
        if (
            "synthesize a complete" in lower
            or "sql query results" in lower
            or "document evidence" in lower
            or ("evidence" in lower and "sql" in lower and "rag passages" in lower)
        ):
            schema_present = (
                "sql query results" in lower
                and "no structured data" not in lower
                and "sql query:" in lower
            )
            return _build_synthesis(original, schema_present)

        # ── 3. SQL generation ─────────────────────────────────────────────────
        if (
            "generate sql" in lower
            or "generate a single" in lower
            or "only the sql query" in lower
            or ("only select statements" in lower and "schema" in lower)
        ):
            return _pick_sql(lower)

        # ── 4. Business glossary ──────────────────────────────────────────────
        if "glossary" in lower or "business term" in lower or "definition" in lower:
            return (
                "Revenue: Total income generated from business operations before any deductions. "
                "EBITDA: Earnings Before Interest, Taxes, Depreciation and Amortization — "
                "a proxy for operating cash flow. "
                "Gross Margin: Gross profit as a percentage of revenue."
            )

        # ── 5. Default ────────────────────────────────────────────────────────
        return (
            "Based on the available enterprise data, the requested financial metrics have been "
            "retrieved from the structured database and document repository. "
            "The analysis indicates strong financial performance across the tracked companies, "
            "with Apex Analytics Corp demonstrating the highest YoY growth rate at 22%. "
            "Set EIO_ACTIVE_LLM=gpt_oss with HF_TOKEN or EIO_ACTIVE_LLM=openai with "
            "OPENAI_API_KEY in .env for full AI-powered natural language responses."
        )

    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse:
        """
        Real semantic embeddings via sentence-transformers/all-MiniLM-L6-v2.
        Falls back to deterministic hash vectors if sentence-transformers unavailable.
        No API key needed — 22 MB model runs on CPU in ~5 ms.
        """
        try:
            from eio.connectors.llm.gptoss_provider import get_sentence_embedding
            return get_sentence_embedding(text, provider_name=self.provider_name)
        except Exception:
            return EmbeddingResponse(
                embedding=_mock_embedding(text),
                model="hash-embed-384",
                provider=self.provider_name,
                input_tokens=len(text.split()),
                cost_usd=0.0,
            )

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.provider_name,
            "model": self.default_model,
            "note": "Mock provider — no API key required",
        }
