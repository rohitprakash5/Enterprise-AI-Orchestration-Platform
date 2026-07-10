"""
Semantic Schema Agent
======================
Enriches raw schema metadata with business term mappings from the
enterprise glossary. Produces a combined context string that the
SQL Generation Agent uses to write accurate, business-aligned queries.

Example: maps "revenue" → transactions.amount WHERE type='revenue'
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from eio.agents.base import AgentContext, AgentResult, BaseAgent
from eio.core.registries import AgentRegistry

logger = logging.getLogger(__name__)

_DEFAULT_GLOSSARY_PATH = "eio/data/demo/business_glossary.json"


@AgentRegistry.register("semantic_schema")
class SemanticSchemaAgent(BaseAgent):
    """
    Maps business terms detected in the user query to schema columns
    using a glossary file, enriching the SQL generation context.
    """

    def __init__(self, glossary_path: str | None = None) -> None:
        self._glossary_path = glossary_path or _DEFAULT_GLOSSARY_PATH
        self._glossary: dict[str, dict] = {}
        self._load_glossary()

    @property
    def agent_name(self) -> str:
        return "semantic_schema"

    def _load_glossary(self) -> None:
        path = Path(self._glossary_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._glossary = json.load(f)
        else:
            logger.warning(f"Glossary file not found: {self._glossary_path}")

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(
            context,
            input_summary=f"Mapping business terms in query: {context.user_query[:80]}",
        )

        if not context.schema_info:
            self._end(context, step, output_summary="No schema available — skipped")
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                output_summary="No schema available, skipped",
            )

        # Detect business terms mentioned in the user query
        query_lower = context.user_query.lower()
        matched_terms: dict[str, dict] = {}
        for term, definition in self._glossary.items():
            if term.lower() in query_lower:
                matched_terms[term] = definition

        # Build enriched context string
        lines: list[str] = [context.schema_context_str, ""]
        if matched_terms:
            lines.append("Business Term Mappings (from Enterprise Glossary):")
            for term, defn in matched_terms.items():
                mapping = defn.get("sql_mapping", "")
                description = defn.get("description", "")
                lines.append(f"  - '{term}': {description}")
                if mapping:
                    lines.append(f"    SQL: {mapping}")
            context.glossary_context = "\n".join(
                f"{term}: {defn.get('description', '')}"
                for term, defn in matched_terms.items()
            )

        context.schema_context_str = "\n".join(lines)

        summary = (
            f"Matched {len(matched_terms)} business term(s): {list(matched_terms.keys())}"
            if matched_terms
            else "No business terms matched in query"
        )

        self._end(context, step, output_summary=summary)
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=matched_terms,
            output_summary=summary,
            metadata={"matched_terms": list(matched_terms.keys())},
        )
