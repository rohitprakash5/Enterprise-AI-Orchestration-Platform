"""
EIO Agents Package
===================
Importing this package registers all agents into the AgentRegistry.
New agents are added by creating a file here with @AgentRegistry.register("name").
No changes to the Orchestrator or any other platform component are needed.
"""

# Import all agents to trigger @AgentRegistry.register decorators
from eio.agents.business_glossary_agent import BusinessGlossaryAgent
from eio.agents.data_quality_agent import DataQualityAgent
from eio.agents.database_execution_agent import DatabaseExecutionAgent
from eio.agents.document_retrieval_agent import DocumentRetrievalAgent
from eio.agents.lineage_agent import LineageAgent
from eio.agents.metadata_discovery_agent import MetadataDiscoveryAgent
from eio.agents.migration_reconciliation_agent import MigrationReconciliationAgent
from eio.agents.planner_agent import PlannerAgent
from eio.agents.rag_agent import RAGAgent
from eio.agents.response_synthesis_agent import ResponseSynthesisAgent
from eio.agents.semantic_schema_agent import SemanticSchemaAgent
from eio.agents.sql_generation_agent import SQLGenerationAgent
from eio.agents.sql_validation_agent import SQLValidationAgent

__all__ = [
    "PlannerAgent",
    "MetadataDiscoveryAgent",
    "SemanticSchemaAgent",
    "SQLGenerationAgent",
    "SQLValidationAgent",
    "DatabaseExecutionAgent",
    "DocumentRetrievalAgent",
    "RAGAgent",
    "BusinessGlossaryAgent",
    "DataQualityAgent",
    "LineageAgent",
    "MigrationReconciliationAgent",
    "ResponseSynthesisAgent",
]
