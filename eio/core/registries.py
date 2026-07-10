"""
EIO Core Registries
=====================
Three independent registries form the backbone of EIO's plug-in architecture:

  CapabilityRegistry — what the platform CAN do (sql_query, document_retrieval, etc.)
  ToolRegistry       — HOW it does it (concrete tool implementations)
  AgentRegistry      — WHO executes it (agent classes registered by name)

This separation mirrors the user's stated design:
  User → Planner → CapabilityRegistry → ToolRegistry → AgentRegistry → LLMRouter

Adding a new agent/tool requires ONLY:
  1. Implement the class
  2. Register it in the appropriate registry
  3. No changes to the core platform
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Capability Registry ──────────────────────────────────────────────────────

class CapabilityType(str, Enum):
    SQL_QUERY           = "sql_query"
    DOCUMENT_RETRIEVAL  = "document_retrieval"
    RAG                 = "rag"
    SCHEMA_DISCOVERY    = "schema_discovery"
    DATA_QUALITY        = "data_quality"
    LINEAGE_TRACKING    = "lineage_tracking"
    RECONCILIATION      = "reconciliation"
    GLOSSARY_LOOKUP     = "glossary_lookup"
    RESPONSE_SYNTHESIS  = "response_synthesis"


@dataclass
class Capability:
    name: CapabilityType
    description: str
    required_tools: list[str]
    required_agents: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """
    Registry of platform capabilities.
    The PlannerAgent uses this to understand what the platform can do
    and which tools/agents are needed to fulfill each capability.
    """

    _capabilities: dict[str, Capability] = {}

    @classmethod
    def register(cls, capability: Capability) -> None:
        cls._capabilities[capability.name.value] = capability

    @classmethod
    def get(cls, name: str) -> Capability | None:
        return cls._capabilities.get(name)

    @classmethod
    def all(cls) -> list[Capability]:
        return list(cls._capabilities.values())

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._capabilities.keys())

    @classmethod
    def describe_all(cls) -> str:
        """Human-readable capability summary for LLM prompts."""
        lines = []
        for cap in cls._capabilities.values():
            lines.append(f"- {cap.name.value}: {cap.description}")
        return "\n".join(lines)


# ─── Tool Registry ────────────────────────────────────────────────────────────

@dataclass
class ToolDefinition:
    name: str
    description: str
    capability: CapabilityType
    parameters: dict[str, str] = field(default_factory=dict)   # param_name -> type hint string
    is_available: bool = True


class ToolRegistry:
    """
    Registry of tool definitions available to agents.
    The PlannerAgent inspects this to understand what concrete tools are available.
    """

    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> ToolDefinition | None:
        return cls._tools.get(name)

    @classmethod
    def all(cls) -> list[ToolDefinition]:
        return list(cls._tools.values())

    @classmethod
    def for_capability(cls, capability: CapabilityType) -> list[ToolDefinition]:
        return [t for t in cls._tools.values() if t.capability == capability]

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._tools.keys())

    @classmethod
    def describe_all(cls) -> str:
        lines = []
        for tool in cls._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in tool.parameters.items())
            lines.append(f"- {tool.name}({params}): {tool.description}")
        return "\n".join(lines)


# ─── Agent Registry ───────────────────────────────────────────────────────────

class AgentRegistry:
    """
    Registry of agent classes.
    The Orchestrator uses this to instantiate agents by name,
    enabling dynamic DAG construction without hard-coded imports.
    """

    _agents: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator: @AgentRegistry.register('planner')"""
        def decorator(agent_class: type) -> type:
            cls._agents[name.lower()] = agent_class
            return agent_class
        return decorator

    @classmethod
    def get(cls, name: str) -> type:
        key = name.lower()
        if key not in cls._agents:
            available = ", ".join(cls._agents.keys())
            raise ValueError(
                f"Unknown agent '{name}'. Available: {available}. "
                f"Register the agent with @AgentRegistry.register('{name}')."
            )
        return cls._agents[key]

    @classmethod
    def instantiate(cls, name: str, **kwargs: Any):
        """Instantiate a registered agent by name with optional kwargs."""
        return cls.get(name)(**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._agents.keys())


# ─── Bootstrap: register built-in capabilities and tools ─────────────────────

def bootstrap_registries() -> None:
    """
    Register all built-in platform capabilities and tools.
    Called once at application startup.
    Adding new capabilities/tools requires only adding entries here.
    """

    # Capabilities
    CapabilityRegistry.register(Capability(
        name=CapabilityType.SQL_QUERY,
        description="Generate and execute SQL queries against structured databases",
        required_tools=["generate_sql", "validate_sql", "execute_sql"],
        required_agents=["metadata_discovery", "semantic_schema", "sql_generation",
                         "sql_validation", "database_execution"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.SCHEMA_DISCOVERY,
        description="Discover and introspect database schema structure",
        required_tools=["get_schema"],
        required_agents=["metadata_discovery"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.DOCUMENT_RETRIEVAL,
        description="Retrieve relevant documents from enterprise document repositories",
        required_tools=["list_documents", "read_document"],
        required_agents=["document_retrieval"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.RAG,
        description="Retrieve relevant passages from documents using vector similarity search",
        required_tools=["embed_text", "query_vector_store"],
        required_agents=["rag"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.DATA_QUALITY,
        description="Assess data quality: null checks, outlier detection, freshness validation",
        required_tools=["check_data_quality"],
        required_agents=["data_quality"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.LINEAGE_TRACKING,
        description="Track data lineage: record what data was read from where",
        required_tools=["record_lineage"],
        required_agents=["lineage"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.GLOSSARY_LOOKUP,
        description="Resolve business term definitions from the enterprise glossary",
        required_tools=["lookup_glossary_term"],
        required_agents=["business_glossary"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.RECONCILIATION,
        description="Compare and reconcile query results across multiple data sources",
        required_tools=["reconcile_results"],
        required_agents=["migration_reconciliation"],
    ))
    CapabilityRegistry.register(Capability(
        name=CapabilityType.RESPONSE_SYNTHESIS,
        description="Synthesize structured and unstructured evidence into a natural language answer",
        required_tools=["synthesize_response"],
        required_agents=["response_synthesis"],
    ))

    # Tools
    ToolRegistry.register(ToolDefinition(
        name="get_schema", description="Introspect database schema",
        capability=CapabilityType.SCHEMA_DISCOVERY,
        parameters={}
    ))
    ToolRegistry.register(ToolDefinition(
        name="generate_sql", description="Generate SQL from natural language + schema context",
        capability=CapabilityType.SQL_QUERY,
        parameters={"query": "str", "schema": "str", "glossary": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="validate_sql", description="Validate SQL syntax and safety",
        capability=CapabilityType.SQL_QUERY,
        parameters={"sql": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="execute_sql", description="Execute validated SQL and return results",
        capability=CapabilityType.SQL_QUERY,
        parameters={"sql": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="list_documents", description="List all documents in the storage repository",
        capability=CapabilityType.DOCUMENT_RETRIEVAL,
        parameters={"prefix": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="embed_text", description="Generate embedding vector for text",
        capability=CapabilityType.RAG,
        parameters={"text": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="query_vector_store", description="Query ChromaDB for top-k similar passages",
        capability=CapabilityType.RAG,
        parameters={"query": "str", "top_k": "int"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="check_data_quality", description="Run data quality checks on query results",
        capability=CapabilityType.DATA_QUALITY,
        parameters={"results": "QueryResult"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="record_lineage", description="Record data access lineage entry",
        capability=CapabilityType.LINEAGE_TRACKING,
        parameters={"source": "str", "operation": "str", "details": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="lookup_glossary_term", description="Look up business term definition",
        capability=CapabilityType.GLOSSARY_LOOKUP,
        parameters={"term": "str"}
    ))
    ToolRegistry.register(ToolDefinition(
        name="synthesize_response", description="Synthesize final answer from all evidence",
        capability=CapabilityType.RESPONSE_SYNTHESIS,
        parameters={"query": "str", "sql_results": "str", "rag_passages": "str"}
    ))
