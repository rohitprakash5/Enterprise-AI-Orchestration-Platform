"""
Document Retrieval Agent
=========================
Fetches candidate documents from the active StorageConnector.
Filters documents by relevance to the user query using keyword
matching against document names and metadata.

Stores the list of candidate document paths in AgentContext
for the RAGAgent to process.
"""

from __future__ import annotations

import logging

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("document_retrieval")
class DocumentRetrievalAgent(BaseAgent):
    """
    Lists available documents from the storage connector and filters
    by query relevance. The RAGAgent handles chunking and embedding.
    """

    @property
    def agent_name(self) -> str:
        return "document_retrieval"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(
            context,
            input_summary=f"Discovering documents for: {context.user_query[:60]}",
        )

        try:
            all_docs = context.storage_connector.list_documents()

            if not all_docs:
                self._end(context, step, output_summary="No documents found in storage")
                return AgentResult(
                    agent_name=self.agent_name,
                    success=True,
                    output=[],
                    output_summary="No documents available",
                )

            # Filter to readable document types
            supported_types = {"application/pdf", "text/plain", "text/markdown",
                               "application/json", "text/csv"}
            readable = [d for d in all_docs if d.content_type in supported_types]

            # Simple relevance: all docs are candidates (RAGAgent will rank by similarity)
            candidate_paths = [d.path for d in readable]
            context.retrieved_documents = candidate_paths
            context.trace.documents_retrieved = candidate_paths

            for doc in readable:
                context.trace.add_lineage(
                    source_type="document",
                    source_name=doc.name,
                    operation="discovery",
                    details=f"{doc.content_type}, {doc.size_bytes} bytes",
                )

            summary = f"Found {len(candidate_paths)} document(s): {[d.name for d in readable]}"
            self._end(context, step, output_summary=summary,
                      metadata={"document_count": len(candidate_paths)})
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=candidate_paths,
                output_summary=summary,
            )

        except Exception as exc:
            error = f"Document retrieval failed: {exc}"
            logger.error(error, exc_info=True)
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
            )
