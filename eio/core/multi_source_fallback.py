"""
Multi-Source Fallback Engine
=============================
When the primary evidence source (e.g. analyst report) is unavailable,
the engine cascades through a priority-ordered list of secondary sources,
accumulating evidence and recalculating confidence at each step.

After exhausting all automatic sources, if confidence is above a minimum
threshold but below the "full confidence" bar, it surfaces a user
confirmation prompt:

    "Primary evidence unavailable.
     Generate a best-effort answer using secondary sources? (81% confidence)"

The engine is stateless — it operates on the AgentContext documents /
SQL results already gathered and the planner's source priority list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Source catalogue — ordered by typical enterprise quality for financial /
# strategic queries.  Weights represent the marginal confidence contribution
# of each source being present.
# ---------------------------------------------------------------------------

SOURCE_CATALOGUE: list[dict[str, Any]] = [
    {
        "id":          "analyst_report",
        "name":        "Analyst Report",
        "priority":    1,
        "weight":      0.40,
        "keywords":    ["analyst", "analyst report", "research report", "equity research"],
        "doc_patterns": ["analyst", "research", "equity"],
        "connector":   None,
    },
    {
        "id":          "annual_report",
        "name":        "Annual Report",
        "priority":    2,
        "weight":      0.30,
        "keywords":    ["annual report", "annual", "10-k", "10k", "yearly report"],
        "doc_patterns": ["annual", "annual_report", "10k"],
        "connector":   None,
    },
    {
        "id":          "company_overview",
        "name":        "Company Overview",
        "priority":    3,
        "weight":      0.15,
        "keywords":    ["company overview", "overview", "company profile", "about"],
        "doc_patterns": ["overview", "company", "profile"],
        "connector":   None,
    },
    {
        "id":          "quarterly_earnings",
        "name":        "Quarterly Earnings",
        "priority":    4,
        "weight":      0.25,
        "keywords":    ["earnings", "quarterly", "q4", "q1", "q2", "q3", "results"],
        "doc_patterns": ["earnings", "quarterly", "q4", "q1", "q2", "q3"],
        "connector":   None,
    },
    {
        "id":          "financial_database",
        "name":        "Financial Database",
        "priority":    5,
        "weight":      0.35,
        "keywords":    ["revenue", "ebitda", "profit", "margin", "financial", "expense"],
        "doc_patterns": [],
        "connector":   "database",
    },
    {
        "id":          "sharepoint",
        "name":        "SharePoint",
        "priority":    6,
        "weight":      0.20,
        "keywords":    ["sharepoint", "intranet", "internal documents"],
        "doc_patterns": [],
        "connector":   "sharepoint",
    },
    {
        "id":          "snowflake",
        "name":        "Snowflake",
        "priority":    7,
        "weight":      0.25,
        "keywords":    ["snowflake", "data warehouse", "dwh", "warehouse"],
        "doc_patterns": [],
        "connector":   "snowflake",
    },
    {
        "id":          "risk_policy",
        "name":        "Risk & Policy Docs",
        "priority":    8,
        "weight":      0.15,
        "keywords":    ["risk", "policy", "governance", "compliance", "regulatory"],
        "doc_patterns": ["risk", "policy", "governance", "compliance"],
        "connector":   None,
    },
    {
        "id":          "investment_thesis",
        "name":        "Investment Thesis",
        "priority":    9,
        "weight":      0.20,
        "keywords":    ["investment", "thesis", "valuation", "target price"],
        "doc_patterns": ["investment", "thesis"],
        "connector":   None,
    },
]

# Confidence thresholds
CONFIDENCE_FLOOR    = 0.40   # below this → do not proceed even with user confirmation
CONFIDENCE_PROCEED  = 0.65   # above this → proceed automatically
CONFIDENCE_FULL     = 0.90   # above this → skip user prompt entirely


@dataclass
class SourceSearchResult:
    """Result of searching one evidence source."""
    source_id:    str
    source_name:  str
    priority:     int
    found:        bool
    confidence_contribution: float = 0.0
    details:      str = ""


@dataclass
class FallbackState:
    """
    Complete state of the multi-source fallback process.
    Stored on AgentContext.trace and returned in the API response.
    """
    triggered:              bool = False
    primary_source_missing: str = ""           # name of the source that triggered fallback
    sources_searched:       list[SourceSearchResult] = field(default_factory=list)
    accumulated_confidence: float = 0.0
    requires_user_confirmation: bool = False
    user_confirmed:         bool = False       # set by API caller if confirmation granted
    best_effort_answer:     bool = False       # True when answer generated from secondaries
    confirmation_message:   str = ""
    secondary_sources_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "triggered":                self.triggered,
            "primary_source_missing":   self.primary_source_missing,
            "sources_searched": [
                {
                    "source_id":   r.source_id,
                    "source_name": r.source_name,
                    "priority":    r.priority,
                    "found":       r.found,
                    "confidence_contribution": round(r.confidence_contribution, 3),
                    "details":     r.details,
                }
                for r in self.sources_searched
            ],
            "accumulated_confidence":       round(self.accumulated_confidence, 3),
            "requires_user_confirmation":   self.requires_user_confirmation,
            "user_confirmed":               self.user_confirmed,
            "best_effort_answer":           self.best_effort_answer,
            "confirmation_message":         self.confirmation_message,
            "secondary_sources_used":       self.secondary_sources_used,
        }


class MultiSourceFallbackEngine:
    """
    Cascades through source_priority list, checking availability of each source
    in the agent context (documents already retrieved, SQL result present, etc.).
    Returns a FallbackState describing what was found and whether to proceed.
    """

    def evaluate(
        self,
        query: str,
        available_docs: list[str],
        has_sql_data: bool,
        source_priorities: list[dict[str, Any]],
        user_confirmed: bool = False,
    ) -> FallbackState:
        """
        Parameters
        ----------
        query            : original user query (used for keyword matching)
        available_docs   : list of document filenames available in storage
        has_sql_data     : whether a database result was returned
        source_priorities: from PlannerAgent — ordered list of {name, priority, ...}
        user_confirmed   : True if the user already approved a best-effort answer
        """
        state = FallbackState()
        if not source_priorities:
            return state

        docs_lower = " ".join(d.lower() for d in available_docs)
        query_lower = query.lower()
        accumulated = 0.0
        found_any   = False

        # Determine which sources the query actually needs
        relevant_sources = self._relevant_sources(query_lower, source_priorities)

        if not relevant_sources:
            return state

        # Check primary source first
        primary = relevant_sources[0]
        primary_found = self._check_source(primary, docs_lower, has_sql_data)

        if primary_found:
            # Primary available — no fallback needed
            return state

        # Primary missing — trigger fallback
        state.triggered = True
        state.primary_source_missing = primary["name"]

        state.sources_searched.append(SourceSearchResult(
            source_id=primary.get("id", primary["name"].lower().replace(" ", "_")),
            source_name=primary["name"],
            priority=1,
            found=False,
            details="Primary source not available in connected storage or database",
        ))

        # Cascade through remaining sources
        for i, src in enumerate(relevant_sources[1:], start=2):
            found = self._check_source(src, docs_lower, has_sql_data)
            contribution = src.get("weight", 0.20) if found else 0.0
            if found:
                accumulated += contribution
                found_any = True
                state.secondary_sources_used.append(src["name"])

            state.sources_searched.append(SourceSearchResult(
                source_id=src.get("id", src["name"].lower().replace(" ", "_")),
                source_name=src["name"],
                priority=i,
                found=found,
                confidence_contribution=contribution,
                details=(
                    f"Found in {'database' if src.get('connector') == 'database' else 'document storage'}"
                    if found else "Not available"
                ),
            ))

        state.accumulated_confidence = min(1.0, accumulated)

        # Decide whether to ask user
        if state.accumulated_confidence < CONFIDENCE_FLOOR:
            state.requires_user_confirmation = False
            state.best_effort_answer = False
            state.confirmation_message = (
                f"Insufficient secondary evidence found "
                f"(confidence {round(state.accumulated_confidence * 100)}%). "
                f"Cannot generate a reliable answer."
            )
        elif state.accumulated_confidence < CONFIDENCE_PROCEED:
            pct = round(state.accumulated_confidence * 100)
            sources_txt = ", ".join(state.secondary_sources_used) or "no secondary sources"
            state.requires_user_confirmation = not user_confirmed
            state.user_confirmed = user_confirmed
            state.best_effort_answer = user_confirmed
            state.confirmation_message = (
                f"Primary evidence unavailable ({state.primary_source_missing} missing).\n"
                f"Generate a best-effort answer using secondary sources "
                f"({sources_txt})?\n"
                f"Confidence: {pct}%\nProceed?"
            )
        else:
            # Enough secondary evidence — proceed automatically
            pct = round(state.accumulated_confidence * 100)
            state.requires_user_confirmation = False
            state.best_effort_answer = True
            state.confirmation_message = (
                f"Primary source ({state.primary_source_missing}) unavailable. "
                f"Proceeding with secondary sources at {pct}% confidence."
            )

        return state

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _relevant_sources(
        query_lower: str,
        source_priorities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return the subset of source_priorities relevant to the query, in order."""
        # Use the planner's priority list directly; it's already query-tuned
        return sorted(source_priorities, key=lambda s: s.get("priority", 99))

    @staticmethod
    def _check_source(
        source: dict[str, Any],
        docs_lower: str,
        has_sql_data: bool,
    ) -> bool:
        """Check whether a source has data available."""
        connector = source.get("connector")
        if connector == "database":
            return has_sql_data
        if connector in ("sharepoint", "snowflake"):
            return False  # not yet connected — always missing unless explicitly wired
        # Document-based source: check filenames
        patterns = source.get("doc_patterns", [])
        if not patterns:
            # Fall back to keyword check on doc names
            patterns = [w for w in source["name"].lower().split() if len(w) > 3]
        return any(p in docs_lower for p in patterns)
