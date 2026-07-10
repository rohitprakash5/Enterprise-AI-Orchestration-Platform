"""
Business Glossary Agent
========================
Resolves business term definitions from the enterprise glossary.
Used for explainability annotation and to enrich the query context.

Modular interface — extend by replacing the JSON glossary file
with a database-backed or API-backed glossary service.
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


@AgentRegistry.register("business_glossary")
class BusinessGlossaryAgent(BaseAgent):
    """
    Looks up business term definitions from a JSON glossary file.
    Detected terms are stored in AgentContext for downstream use.
    """

    def __init__(self, glossary_path: str | None = None) -> None:
        self._glossary_path = glossary_path or _DEFAULT_GLOSSARY_PATH
        self._glossary: dict[str, dict] = self._load()

    @property
    def agent_name(self) -> str:
        return "business_glossary"

    def _load(self) -> dict[str, dict]:
        path = Path(self._glossary_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def lookup(self, term: str) -> dict | None:
        """Public API: look up a single term by name."""
        return self._glossary.get(term.lower())

    def run(self, context: AgentContext) -> AgentResult:
        step = self._begin(context, input_summary=f"Glossary lookup for: {context.user_query[:60]}")

        query_lower = context.user_query.lower()
        matched: dict[str, str] = {}

        for term, defn in self._glossary.items():
            if re.search(rf"\b{re.escape(term.lower())}\b", query_lower):
                matched[term] = defn.get("description", "")

        if matched:
            context.glossary_context = "\n".join(
                f"{term}: {desc}" for term, desc in matched.items()
            )
        else:
            context.glossary_context = ""

        summary = (
            f"Resolved {len(matched)} term(s): {list(matched.keys())}"
            if matched else "No glossary terms matched"
        )
        self._end(context, step, output_summary=summary)
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            output=matched,
            output_summary=summary,
            metadata={"matched_terms": list(matched.keys())},
        )
