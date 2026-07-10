"""
Agent Base Framework
=====================
Defines the BaseAgent ABC, AgentContext (shared state bag), and AgentResult.

Every agent:
  - Receives an AgentContext on every .run() call
  - Appends its AgentStep to the embedded ExplainabilityTrace
  - Returns an AgentResult with output and metadata
  - Raises NO unhandled exceptions — errors are captured in the trace

Adding a new agent:
  1. Create a new file in eio/agents/
  2. Subclass BaseAgent
  3. Implement run(context) -> AgentResult
  4. Decorate with @AgentRegistry.register("your_agent_name")
  5. No other platform changes are needed
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from eio.connectors.databases.base import QueryResult, SchemaInfo
from eio.connectors.llm.base import RoutingContext, RoutingDecision
from eio.connectors.llm.base import LLMProvider
from eio.connectors.databases.base import DatabaseConnector
from eio.connectors.storage.base import StorageConnector
from eio.core.explainability.trace import ExplainabilityTrace, RAGPassage


class AgentContext(BaseModel):
    """
    Central shared state passed between all agents.
    Agents read from and write to this context throughout the request lifecycle.
    The Orchestrator initializes it and returns it with the final response.
    """

    model_config = {"arbitrary_types_allowed": True}

    # Request identity
    request_id: str = ""
    session_id: str = ""
    user_id: str = ""
    user_query: str = ""

    # Infrastructure (injected by the Orchestrator at startup)
    db_connector: Any = None          # DatabaseConnector instance
    storage_connector: Any = None     # StorageConnector instance
    llm_provider: Any = None          # LLMProvider instance
    vector_collection: Any = None     # ChromaDB Collection instance

    # Planning outputs
    routing_context: RoutingContext | None = None
    routing_decision: RoutingDecision | None = None
    selected_agents: list[str] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    selected_capabilities: list[str] = Field(default_factory=list)

    # Schema context
    schema_info: SchemaInfo | None = None
    schema_context_str: str = ""      # formatted for LLM prompts
    glossary_context: str = ""        # business term definitions

    # SQL pipeline
    sql_generated: str = ""
    sql_validated: bool = False
    sql_result: QueryResult | None = None

    # RAG pipeline
    rag_passages: list[RAGPassage] = Field(default_factory=list)
    retrieved_documents: list[str] = Field(default_factory=list)

    # Data quality & lineage
    data_quality_notes: list[str] = Field(default_factory=list)
    lineage_notes: list[str] = Field(default_factory=list)

    # Final output
    final_answer: str = ""
    confidence_score: float = 0.0

    # Accumulation across agents
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Explainability trace (threaded through all agents)
    trace: ExplainabilityTrace = Field(default_factory=ExplainabilityTrace)

    def add_tokens(self, tokens: int, cost_usd: float) -> None:
        self.total_tokens += tokens
        self.total_cost_usd += cost_usd


class AgentResult(BaseModel):
    """Structured result returned by every agent's .run() method."""

    agent_name: str
    success: bool = True
    output: Any = None
    output_summary: str = ""
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all EIO agents.

    Subclasses implement run() and are registered with AgentRegistry.
    The begin_step / end_step helpers ensure every agent produces a
    consistent trace step without boilerplate.
    """

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique agent identifier string."""

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's responsibility.
        Always returns AgentResult — never raises unhandled exceptions.
        """

    # ── Trace helpers ──────────────────────────────────────────────────────

    def _begin(self, context: AgentContext, input_summary: str = "") -> Any:
        """Start a trace step for this agent."""
        return context.trace.begin_step(self.agent_name, input_summary)

    def _end(
        self,
        context: AgentContext,
        step: Any,
        output_summary: str = "",
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """End a trace step for this agent."""
        context.trace.end_step(step, output_summary, status, error, metadata)

    def _safe_run(self, context: AgentContext) -> AgentResult:
        """
        Wrapper that guarantees an AgentResult is always returned.
        Each agent's run() method manages its own trace step via _begin/_end,
        so _safe_run only catches unhandled exceptions that escape run().
        """
        try:
            return self.run(context)
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            # Write a minimal trace step so the failure is visible in the timeline
            step = context.trace.begin_step(self.agent_name, "unhandled exception")
            context.trace.end_step(step, status="error", error=error_msg)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error_msg,
                output_summary=f"Agent failed: {error_msg}",
            )
