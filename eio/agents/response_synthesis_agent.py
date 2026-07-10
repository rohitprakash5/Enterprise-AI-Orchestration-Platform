"""
Response Synthesis Agent
=========================
The final agent in every EIO pipeline. Combines all available evidence:
  - SQL query results (structured data)
  - RAG passages (unstructured document evidence)
  - Business glossary definitions
  - Data quality notes
  - Lineage information

Produces a single, coherent natural language answer with:
  - Direct answer to the user's question
  - Evidence citations (data source + document source)
  - Confidence qualifier based on data quality
  - A brief reasoning explanation
"""

from __future__ import annotations

import logging

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.connectors.llm.base import LLMRequest, Message, MessageRole
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)

_SYNTHESIS_SYSTEM_PROMPT = """You are a senior enterprise business analyst. Your role is to synthesize evidence from multiple sources into a clear, concise, and accurate business answer.

You will be given:
1. SQL query results (structured financial data)
2. Document passages (from annual reports and enterprise documents)
3. Business term definitions

Your response must:
- Directly answer the user's question in 2-4 paragraphs
- Cite specific numbers from the SQL results (if available)
- Reference specific document passages (if available)
- Acknowledge any data quality limitations
- Be written for a senior executive audience
- End with a brief "Evidence Sources" section listing the data origins

If SQL results are not available, rely solely on document passages.
If document passages are not available, rely solely on SQL results.
If neither is available, clearly state that you cannot answer the question with the available data.
"""

_SYNTHESIS_USER_TEMPLATE = """User Question: {query}

SQL Query Results:
{sql_results}

Document Evidence (RAG Passages):
{rag_passages}

Business Term Definitions:
{glossary}

Data Quality Notes:
{quality_notes}

Please synthesize a complete, evidence-based answer.
"""


@AgentRegistry.register("response_synthesis")
class ResponseSynthesisAgent(BaseAgent):
    """
    Synthesizes structured and unstructured evidence into a final answer.
    Uses the selected LLM with a carefully crafted enterprise analyst prompt.
    """

    @property
    def agent_name(self) -> str:
        return "response_synthesis"

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary=f"Synthesizing response for: {context.user_query[:60]}")

        model = (
            context.routing_decision.model
            if context.routing_decision
            else context.llm_provider.default_model
        )

        # ── Format SQL results ─────────────────────────────────────────────
        sql_section = "No structured data available."
        if context.sql_result and context.sql_result.success:
            sql_section = (
                f"SQL Query: {context.sql_generated}\n\n"
                f"Results:\n{context.sql_result.to_markdown_table()}"
            )

        # ── Format RAG passages ────────────────────────────────────────────
        rag_section = "No document passages available."
        if context.rag_passages:
            parts = []
            for i, passage in enumerate(context.rag_passages[:5], 1):
                parts.append(
                    f"[{i}] Source: {passage.source}"
                    + (f", Page {passage.page}" if passage.page else "")
                    + f" (relevance: {passage.score:.2f})\n{passage.text[:600]}"
                )
            rag_section = "\n\n".join(parts)

        # ── Format quality notes ───────────────────────────────────────────
        quality_section = (
            "\n".join(context.data_quality_notes) if context.data_quality_notes
            else "No data quality issues detected."
        )

        prompt = _SYNTHESIS_USER_TEMPLATE.format(
            query=context.user_query,
            sql_results=sql_section,
            rag_passages=rag_section,
            glossary=context.glossary_context or "No glossary context.",
            quality_notes=quality_section,
        )

        request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content=prompt)],
            model=model,
            temperature=0.1,
            max_tokens=1500,
            system_prompt=_SYNTHESIS_SYSTEM_PROMPT,
        )

        try:
            response = context.llm_provider.complete(request)
            context.add_tokens(response.total_tokens, response.cost_usd)

            context.final_answer = response.content
            context.trace.routing_decision = (
                context.routing_decision.model_dump()
                if context.routing_decision
                else None
            )

            summary = f"Synthesized {len(response.content)} char answer using {model}"
            self._end(context, step, output_summary=summary,
                      metadata={"model": model, "output_length": len(response.content)})

            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output=response.content,
                output_summary=summary,
                metadata={"model_used": model, "finish_reason": response.finish_reason},
            )

        except Exception as exc:
            error = f"Response synthesis failed: {exc}"
            logger.error(error, exc_info=True)
            self._end(context, step, status="error", error=error)
            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                error=error,
            )
