"""
Enterprise Knowledge Advisor
==============================
After every failed or partial query, instead of returning "No data found",
the Knowledge Advisor produces a structured advisory panel:

    Enterprise Knowledge Advisor
    ─────────────────────────────────────────────
    This question cannot be answered because:
      HR Repository      ✗
      Analyst Reports    ✗
      SharePoint         ✗

    Recommendations
    ┌─────────────────────────────────────────┐
    │ Priority: HIGH   Connect SharePoint     │
    │ Business Impact: High                   │
    │ Expected Coverage: +35%                 │
    │ Expected Confidence: +62%               │
    │ Estimated Effort: Low                   │
    └─────────────────────────────────────────┘

It also generates the "Confidence Improvement Projections" that show
exactly how much each missing source would improve the answer quality —
the feature that no other enterprise AI demo currently shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Source gap catalogue — each entry describes one enterprise knowledge source
# with the advisory metadata needed to help data owners act on it.
# ---------------------------------------------------------------------------

_SOURCE_GAP_CATALOGUE: list[dict[str, Any]] = [
    {
        "id":                  "annual_report",
        "name":                "Annual Report",
        "connection_action":   "Upload Annual Report PDF to document storage",
        "priority":            "High",
        "business_impact":     "High",
        "coverage_gain_pct":   30,
        "confidence_gain_pct": 72,
        "effort":              "Low",
        "keywords":            ["annual", "report", "strategy", "outlook", "10-k"],
    },
    {
        "id":                  "analyst_report",
        "name":                "Analyst Report",
        "connection_action":   "Upload Analyst / Equity Research Report",
        "priority":            "High",
        "business_impact":     "High",
        "coverage_gain_pct":   40,
        "confidence_gain_pct": 95,
        "effort":              "Low",
        "keywords":            ["analyst", "equity", "research", "investment thesis", "valuation"],
    },
    {
        "id":                  "sharepoint",
        "name":                "SharePoint",
        "connection_action":   "Connect SharePoint via Microsoft Graph connector",
        "priority":            "High",
        "business_impact":     "High",
        "coverage_gain_pct":   35,
        "confidence_gain_pct": 62,
        "effort":              "Low",
        "keywords":            ["internal", "documents", "policy", "sharepoint", "company"],
    },
    {
        "id":                  "snowflake",
        "name":                "Snowflake Data Warehouse",
        "connection_action":   "Configure Snowflake connector (EIO_ACTIVE_DB=snowflake)",
        "priority":            "Medium",
        "business_impact":     "High",
        "coverage_gain_pct":   25,
        "confidence_gain_pct": 98,
        "effort":              "Medium",
        "keywords":            ["data warehouse", "snowflake", "analytics", "dwh"],
    },
    {
        "id":                  "hr_repository",
        "name":                "HR Repository",
        "connection_action":   "Connect SAP HCM or Workday HR connector",
        "priority":            "Medium",
        "business_impact":     "High",
        "coverage_gain_pct":   20,
        "confidence_gain_pct": 55,
        "effort":              "Medium",
        "keywords":            ["employee", "headcount", "staff", "hr", "payroll", "workforce"],
    },
    {
        "id":                  "crm",
        "name":                "CRM / Sales Data",
        "connection_action":   "Connect Salesforce CRM connector",
        "priority":            "Medium",
        "business_impact":     "Medium",
        "coverage_gain_pct":   15,
        "confidence_gain_pct": 45,
        "effort":              "Medium",
        "keywords":            ["sales", "pipeline", "crm", "customer", "deals", "orders"],
    },
    {
        "id":                  "quarterly_earnings",
        "name":                "Quarterly Earnings Release",
        "connection_action":   "Upload quarterly earnings release documents",
        "priority":            "High",
        "business_impact":     "High",
        "coverage_gain_pct":   25,
        "confidence_gain_pct": 68,
        "effort":              "Low",
        "keywords":            ["quarterly", "earnings", "q1", "q2", "q3", "q4", "results"],
    },
    {
        "id":                  "risk_policy",
        "name":                "Risk & Compliance Docs",
        "connection_action":   "Upload risk policies and compliance documentation",
        "priority":            "Medium",
        "business_impact":     "Medium",
        "coverage_gain_pct":   18,
        "confidence_gain_pct": 40,
        "effort":              "Low",
        "keywords":            ["risk", "compliance", "policy", "regulatory", "governance", "audit"],
    },
    {
        "id":                  "investment_thesis",
        "name":                "Investment Thesis",
        "connection_action":   "Upload investment thesis or valuation report",
        "priority":            "High",
        "business_impact":     "High",
        "coverage_gain_pct":   35,
        "confidence_gain_pct": 80,
        "effort":              "Low",
        "keywords":            ["investment", "thesis", "valuation", "target price", "growth"],
    },
]


@dataclass
class SourceGapRecommendation:
    """A single actionable source gap recommendation."""
    source_id:             str
    source_name:           str
    connection_action:     str
    priority:              str    # "High" | "Medium" | "Low"
    business_impact:       str    # "High" | "Medium" | "Low"
    coverage_gain_pct:     int    # expected % coverage increase
    confidence_gain_pct:   int    # expected confidence score if connected
    effort:                str    # "Low" | "Medium" | "High"
    why_missing:           str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id":           self.source_id,
            "source_name":         self.source_name,
            "connection_action":   self.connection_action,
            "priority":            self.priority,
            "business_impact":     self.business_impact,
            "coverage_gain_pct":   self.coverage_gain_pct,
            "confidence_gain_pct": self.confidence_gain_pct,
            "effort":              self.effort,
            "why_missing":         self.why_missing,
        }


@dataclass
class ConfidenceProjection:
    """Shows how confidence changes as each missing source is added."""
    source_name:          str
    confidence_if_added:  int    # projected confidence % after adding this source
    delta_pct:            int    # improvement over current confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name":         self.source_name,
            "confidence_if_added": self.confidence_if_added,
            "delta_pct":           self.delta_pct,
        }


@dataclass
class KnowledgeAdvisoryReport:
    """
    The full advisory output surfaced after every failed or partial query.
    Replaces the generic "No data found" message.
    """
    query:                     str
    current_confidence_pct:    int
    blocking_sources:          list[str]           # sources that are missing and required
    recommendations:           list[SourceGapRecommendation]
    confidence_projections:    list[ConfidenceProjection]
    advisory_headline:         str = ""
    advisory_detail:           str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query":                    self.query,
            "current_confidence_pct":   self.current_confidence_pct,
            "blocking_sources":         self.blocking_sources,
            "advisory_headline":        self.advisory_headline,
            "advisory_detail":          self.advisory_detail,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "confidence_projections":   [p.to_dict() for p in self.confidence_projections],
        }

    def format_as_text(self) -> str:
        """Human-readable advisory for the final_answer field."""
        lines = [
            "## Enterprise Knowledge Advisor\n",
            f"**{self.advisory_headline}**\n",
        ]
        if self.blocking_sources:
            lines.append("**This question cannot be answered because these sources are unavailable:**")
            for src in self.blocking_sources:
                lines.append(f"  ✗ {src}")
        lines.append("")
        if self.recommendations:
            lines.append("**Recommendations to unlock this answer:**")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(
                    f"\n  **Priority {i} — {rec.priority}**: {rec.connection_action}\n"
                    f"  Business Impact: {rec.business_impact} | "
                    f"Expected Coverage: +{rec.coverage_gain_pct}% | "
                    f"Expected Confidence: {rec.confidence_gain_pct}% | "
                    f"Effort: {rec.effort}"
                )
        if self.confidence_projections:
            lines.append("\n**Confidence Improvement Projections:**")
            lines.append(f"  Current Confidence: {self.current_confidence_pct}%")
            for proj in self.confidence_projections:
                lines.append(
                    f"  If {proj.source_name} added → {proj.confidence_if_added}% "
                    f"(+{proj.delta_pct}%)"
                )
        return "\n".join(lines)


class EnterpriseKnowledgeAdvisor:
    """
    Generates structured, actionable advisory reports for failed or partial queries.
    Called by the Orchestrator whenever is_feasible=False or confidence < threshold.
    """

    def advise(
        self,
        query: str,
        missing_evidence: list[str],
        current_confidence: float,
        available_docs: list[str],
        has_sql_data: bool,
    ) -> KnowledgeAdvisoryReport:
        """
        Build the advisory report.

        Parameters
        ----------
        query              : original user query
        missing_evidence   : list of missing evidence items from the planner
        current_confidence : 0.0–1.0 confidence score from the trace
        available_docs     : document filenames available in storage
        has_sql_data       : whether a database result was returned
        """
        query_lower = query.lower()
        missing_lower = " ".join(missing_evidence).lower()
        combined = query_lower + " " + missing_lower

        # Match missing evidence against source catalogue
        matched: list[dict[str, Any]] = []
        for src in _SOURCE_GAP_CATALOGUE:
            if any(kw in combined for kw in src["keywords"]):
                matched.append(src)

        # Deduplicate and sort by confidence_gain (highest value first)
        seen: set[str] = set()
        unique_matched: list[dict[str, Any]] = []
        for src in sorted(matched, key=lambda s: s["confidence_gain_pct"], reverse=True):
            if src["id"] not in seen:
                seen.add(src["id"])
                unique_matched.append(src)

        # Build blocking sources list
        blocking = [m["name"] for m in unique_matched[:4]]
        if not blocking and missing_evidence:
            blocking = missing_evidence[:3]

        # Build recommendations (top 4)
        recommendations = [
            SourceGapRecommendation(
                source_id=src["id"],
                source_name=src["name"],
                connection_action=src["connection_action"],
                priority=src["priority"],
                business_impact=src["business_impact"],
                coverage_gain_pct=src["coverage_gain_pct"],
                confidence_gain_pct=src["confidence_gain_pct"],
                effort=src["effort"],
                why_missing=f"Not found in connected storage or database",
            )
            for src in unique_matched[:4]
        ]

        # Build confidence projections — show cumulative improvement
        current_pct = round(current_confidence * 100)
        projections: list[ConfidenceProjection] = []
        cumulative = current_pct
        for rec in recommendations:
            new_conf = min(99, rec.confidence_gain_pct)
            delta = max(0, new_conf - cumulative)
            cumulative = new_conf
            projections.append(ConfidenceProjection(
                source_name=rec.source_name,
                confidence_if_added=new_conf,
                delta_pct=delta,
            ))

        headline = (
            "This question cannot be fully answered with the currently connected data sources."
        )
        detail = (
            f"Current answer confidence is {current_pct}%. "
            f"Connecting the recommended sources would bring confidence to "
            f"{projections[-1].confidence_if_added if projections else current_pct}%."
        )

        return KnowledgeAdvisoryReport(
            query=query,
            current_confidence_pct=current_pct,
            blocking_sources=blocking,
            recommendations=recommendations,
            confidence_projections=projections,
            advisory_headline=headline,
            advisory_detail=detail,
        )
