"""
RAG Agent (Retrieval-Augmented Generation)
===========================================
Manages the ChromaDB vector index and retrieves semantically relevant
passages to answer the user's question from enterprise documents.

Lifecycle:
  1. On first call: loads PDFs from storage, chunks them, embeds and upserts
     into ChromaDB. Subsequent calls reuse the persistent index.
  2. On each query: embeds the user question, queries ChromaDB for top-k
     similar chunks, returns RAGPassage objects with source metadata.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import pdfplumber

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.explainability.trace import RAGPassage
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 800       # characters per chunk
_CHUNK_OVERLAP = 100    # overlap to preserve context across boundaries
_TOP_K = 5              # number of passages to retrieve


@AgentRegistry.register("rag")
class RAGAgent(BaseAgent):
    """
    Builds and queries a ChromaDB vector index over enterprise documents.
    Uses the active LLMProvider to generate embeddings.
    """

    @property
    def agent_name(self) -> str:
        return "rag"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(
            context,
            input_summary=f"RAG retrieval for: {context.user_query[:60]}",
        )

        if context.vector_collection is None:
            error = "Vector collection not initialized"
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
            )

        try:
            # ── 1. Index any unindexed documents ───────────────────────
            if context.retrieved_documents:
                self._ensure_indexed(
                    context.retrieved_documents,
                    context.storage_connector,
                    context.llm_provider,
                    context.vector_collection,
                )

            # ── 2. Query the vector store ───────────────────────────────
            embed_response = context.llm_provider.embed(context.user_query)
            context.add_tokens(embed_response.input_tokens, embed_response.cost_usd)

            results = context.vector_collection.query(
                query_embeddings=[embed_response.embedding],
                n_results=min(_TOP_K, context.vector_collection.count() or _TOP_K),
                include=["documents", "metadatas", "distances"],
            )

            passages: list[RAGPassage] = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            for doc_text, meta, dist in zip(docs, metas, dists):
                score = max(0.0, 1.0 - float(dist))  # convert distance to similarity
                passages.append(
                    RAGPassage(
                        text=doc_text,
                        source=meta.get("source", "unknown"),
                        page=meta.get("page"),
                        score=round(score, 3),
                        chunk_index=meta.get("chunk_index", 0),
                    )
                )

            context.rag_passages = passages
            context.trace.rag_passages = passages

            # Record lineage
            sources = list({p.source for p in passages})
            for source in sources:
                context.trace.add_lineage(
                    source_type="vector_store",
                    source_name=source,
                    operation="similarity_search",
                    details=f"Top-{_TOP_K} passages retrieved",
                )

            summary = (
                f"Retrieved {len(passages)} passage(s) from "
                f"{', '.join(sources) or 'no documents'}"
            )
            self._end(context, step, output_summary=summary,
                      metadata={"passage_count": len(passages), "sources": sources})
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=passages,
                output_summary=summary,
            )

        except Exception as exc:
            error = f"RAG retrieval failed: {exc}"
            logger.error(error, exc_info=True)
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
            )

    # ── Indexing helpers ───────────────────────────────────────────────────

    def _ensure_indexed(
        self,
        doc_paths: list[str],
        storage_connector: Any,
        llm_provider: Any,
        collection: Any,
    ) -> None:
        """Index documents that are not yet in the vector collection."""
        existing_ids: set[str] = set()
        try:
            all_ids = collection.get(include=[])
            existing_ids = set(all_ids.get("ids", []))
        except Exception:
            pass

        for path in doc_paths:
            try:
                raw_bytes = storage_connector.read_document(path)
                chunks = self._extract_and_chunk(path, raw_bytes)

                new_chunks = [
                    (chunk_id, text, meta)
                    for chunk_id, text, meta in chunks
                    if chunk_id not in existing_ids
                ]

                if not new_chunks:
                    continue

                embeddings = []
                for chunk_id, text, _ in new_chunks:
                    embed_resp = llm_provider.embed(text)
                    embeddings.append(embed_resp.embedding)

                collection.upsert(
                    ids=[c[0] for c in new_chunks],
                    embeddings=embeddings,
                    documents=[c[1] for c in new_chunks],
                    metadatas=[c[2] for c in new_chunks],
                )
                logger.info(f"Indexed {len(new_chunks)} chunks from {path}")

            except Exception as exc:
                logger.warning(f"Failed to index {path}: {exc}")

    def _extract_and_chunk(
        self, path: str, raw_bytes: bytes
    ) -> list[tuple[str, str, dict]]:
        """Extract text from a document and split into overlapping chunks."""
        ext = Path(path).suffix.lower()
        if ext == ".pdf":
            text_pages = self._extract_pdf(raw_bytes)
        else:
            try:
                text_pages = [(0, raw_bytes.decode("utf-8", errors="ignore"))]
            except Exception:
                return []

        chunks: list[tuple[str, str, dict]] = []
        for page_num, page_text in text_pages:
            page_chunks = self._chunk_text(page_text)
            for i, chunk_text in enumerate(page_chunks):
                chunk_id = hashlib.sha256(
                    f"{path}:{page_num}:{i}:{chunk_text[:50]}".encode()
                ).hexdigest()[:16]
                chunks.append((
                    chunk_id,
                    chunk_text,
                    {"source": Path(path).name, "page": page_num, "chunk_index": i},
                ))
        return chunks

    @staticmethod
    def _extract_pdf(raw_bytes: bytes) -> list[tuple[int, str]]:
        """Extract text from PDF bytes, returning (page_number, text) tuples."""
        import io
        pages: list[tuple[int, str]] = []
        try:
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append((i + 1, text))
        except Exception as exc:
            logger.warning(f"PDF extraction failed: {exc}")
        return pages

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        """Split text into overlapping chunks of _CHUNK_SIZE characters."""
        if len(text) <= _CHUNK_SIZE:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + _CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start += _CHUNK_SIZE - _CHUNK_OVERLAP
        return chunks
