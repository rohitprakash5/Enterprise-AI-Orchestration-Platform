"""
Enterprise Intelligence Orchestrator — Streamlit UI
=====================================================
All 15 enhancements from the Enhancement Request document, fully rendered:

  1.  AI Decision Engine          — 7-dimension scoring matrix, candidates, winner card
  2.  Planner Dashboard           — Intent, skills, tools, execution strategy
  3.  Capability Registry         — Live model capability table from /api/v1/models
  4.  Model Health Registry       — Live health dashboard from /api/v1/models/health
  5.  Cost Optimization Engine    — Per-model cost/latency/accuracy comparison table
  6.  Task-Level Model Routing    — Visual pipeline showing per-stage model assignment
  7.  Enhanced Agent Timeline     — Full infra + agent steps with colour coding
  8.  Database Execution Details  — Connector, type, exec time, rows, cache
  9.  Knowledge Retrieval         — Storage provider, vector DB, passages, confidence
  10. Evidence Summary            — Checklist of all evidence sources used
  11. Governance Dashboard        — Auth, RBAC, Policy Engine, data classification
  12. RBAC / User Context         — User identity, roles, clearance, department
  13. Execution Graph (SVG)       — Top-down colour-coded pipeline graph
  14. Enterprise Observability    — Latency, tokens, cost, calls, agent count
  15. Full sidebar explainability — 4-tab sidebar with all sections
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

# ── API endpoints ────────────────────────────────────────────────────────────
API_URL    = os.getenv("EIO_API_URL", "http://localhost:8000")
QUERY_EP   = f"{API_URL}/api/v1/query"
HEALTH_EP  = f"{API_URL}/api/v1/health/connectors"
CONFIG_EP  = f"{API_URL}/api/v1/config"
MODELS_EP  = f"{API_URL}/api/v1/models"
MHEALTH_EP = f"{API_URL}/api/v1/models/health"

# ── Sample queries ──────────────────────────────────────────────────────────
SAMPLE_QUERIES = [
    "What was total revenue for all companies in Q4 2023?",
    "Compare revenue vs expenses by quarter for all companies in 2023",
    "Which company had the highest YoY revenue growth in 2022?",
    "What does the annual report say about Apex Analytics competitive strategy?",
    "Show EBITDA and gross margin for all companies in Q4 2023",
    "What are the key risk factors described in the risk management policy?",
    "What was the run rate for Apex Analytics based on Q4 2023?",
    "Summarise the investment thesis for Apex Analytics from the analyst report",
]

# ── Agent / infra step icons ─────────────────────────────────────────────────
AGENT_ICONS = {
    "Planner Agent":           "🧠",
    "planner":                 "🧠",
    "Policy Engine":           "🛡️",
    "Policy Engine (SQL)":     "🛡️",
    "Policy Engine (PII)":     "🛡️",
    "AI Decision Engine":      "⚡",
    "Capability Registry":     "📋",
    "Model Health Registry":   "💓",
    "Agent Orchestrator":      "🎯",
    "business_glossary":       "📖",
    "metadata_discovery":      "🔍",
    "semantic_schema":         "🗂️",
    "sql_generation":          "⚙️",
    "sql_validation":          "✅",
    "database_execution":      "🗄️",
    "document_retrieval":      "📂",
    "rag":                     "🔎",
    "data_quality":            "📊",
    "lineage":                 "🔗",
    "migration_reconciliation":"⚖️",
    "response_synthesis":      "💬",
}

STATUS_COLORS = {"success": "🟢", "error": "🔴", "running": "🟡", "skipped": "⚪"}

INFRA_STEPS = {
    "Planner Agent", "Policy Engine", "Policy Engine (SQL)", "Policy Engine (PII)",
    "AI Decision Engine", "Capability Registry", "Model Health Registry",
    "Agent Orchestrator",
}

# ── Node types for SVG graph ─────────────────────────────────────────────────
_NODE_TYPE = {
    "Planner Agent":           "user",
    "planner":                 "planner",
    "Policy Engine":           "infra",
    "Policy Engine (SQL)":     "infra",
    "Policy Engine (PII)":     "infra",
    "AI Decision Engine":      "infra",
    "Capability Registry":     "infra",
    "Model Health Registry":   "infra",
    "Agent Orchestrator":      "infra",
    "metadata_discovery":      "agent",
    "semantic_schema":         "agent",
    "sql_generation":          "agent",
    "sql_validation":          "agent",
    "database_execution":      "data",
    "document_retrieval":      "data",
    "rag":                     "data",
    "data_quality":            "agent",
    "lineage":                 "agent",
    "business_glossary":       "agent",
    "migration_reconciliation":"agent",
    "response_synthesis":      "synthesis",
}

_NODE_COLORS = {
    "user":      ("#1a365d", "#bee3f8"),
    "planner":   ("#2c5282", "#bee3f8"),
    "infra":     ("#553c9a", "#e9d8fd"),
    "agent":     ("#276749", "#c6f6d5"),
    "data":      ("#7b341e", "#feebc8"),
    "synthesis": ("#2d3748", "#e2e8f0"),
}


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="Enterprise Intelligence Orchestrator",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()

    if "history"       not in st.session_state: st.session_state.history = []
    if "last_response" not in st.session_state: st.session_state.last_response = None
    if "query_input"   not in st.session_state: st.session_state.query_input = ""

    _render_sidebar()
    _render_header()
    _render_connector_status()

    col_q, col_r = st.columns([1, 1.7], gap="large")
    with col_q:
        _render_query_panel()
    with col_r:
        if st.session_state.last_response:
            _render_response_panel(st.session_state.last_response)
        else:
            _render_welcome()


# ── Header ───────────────────────────────────────────────────────────────────

def _render_header() -> None:
    st.markdown("""
    <div class="eio-header">
      <h1>🤖 Enterprise Intelligence Orchestrator</h1>
      <p>
        Multi-Agent AI Platform &nbsp;·&nbsp;
        Pluggable Connectors &nbsp;·&nbsp;
        AI Decision Engine &nbsp;·&nbsp;
        Explainable Governance &nbsp;·&nbsp;
        Cost Optimization
      </p>
    </div>""", unsafe_allow_html=True)


# ── Connector status bar ─────────────────────────────────────────────────────

def _render_connector_status() -> None:
    cfg = _safe_get(CONFIG_EP) or {}
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("LLM Provider",    cfg.get("active_llm",     "—").upper())
    c2.metric("Database",        cfg.get("active_db",      "—").upper())
    c3.metric("Storage",         cfg.get("active_storage", "—").upper())
    c4.metric("Agents",          "13 Registered")
    c5.metric("Model Profiles",  "8 Profiles")
    c6.metric("Policy Engine",   "Active")


# ── Welcome ──────────────────────────────────────────────────────────────────

def _render_welcome() -> None:
    st.markdown("""
    <div class="eio-welcome">
      <h3>Enterprise AI Orchestration — Not a Chatbot</h3>
      <p>
        EIO coordinates <strong>13 specialized agents</strong>,
        <strong>8 LLM candidates</strong>,
        heterogeneous databases, document repositories, and
        a governance policy engine to answer complex business questions
        with <strong>fully explainable reasoning</strong>.
      </p>
      <hr style="border-color:#e5e7eb"/>
      <p style="margin:0;font-size:0.85rem;color:#57606a">
        ← Select a sample question or type your own, then click
        <strong>Run Query</strong> to see the full orchestration in action.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Live model registry preview (Enhancement #3 — Capability Registry)
    _render_capability_registry_preview()


def _render_capability_registry_preview() -> None:
    models_data = _safe_get(MODELS_EP) or {}
    profiles = models_data.get("profiles", [])
    if not profiles:
        return
    with st.expander("📋 Model Capability Registry — 8 Registered Models", expanded=True):
        import pandas as pd
        rows = []
        for p in profiles:
            caps = p.get("capabilities", [])
            rows.append({
                "Model":         p.get("display_name", ""),
                "Provider":      p.get("provider", "").upper(),
                "Context":       f"{p.get('context_window', 0) // 1000}k",
                "SQL": "✓" if "SQL Generation" in caps else "·",
                "RAG": "✓" if "RAG Support"    in caps else "·",
                "Vision": "✓" if "Vision"       in caps else "·",
                "Code": "✓" if "Code Generation" in caps else "·",
                "Reasoning": "✓" if "Multi-step Reasoning" in caps else "·",
                "Cost/1k (in)":  f"${p.get('cost_per_1k_input',0):.4f}",
                "Latency (ms)":  p.get("avg_latency_ms", 0),
                "Gov ✓":  "✅" if p.get("governance_approved") else "❌",
                "Notes":         p.get("notes", "")[:55],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── Query panel ──────────────────────────────────────────────────────────────

def _render_query_panel() -> None:
    st.subheader("📝 Business Query")

    with st.expander("💡 Sample Questions", expanded=True):
        for sample in SAMPLE_QUERIES:
            label = sample if len(sample) <= 68 else sample[:65] + "…"
            if st.button(f"→ {label}", key=f"sq_{sample[:20]}"):
                # Write directly into the widget's own state key so it appears immediately
                st.session_state["_query_ta"] = sample
                st.session_state.query_input  = sample

    # Use a stable key; pre-populate from session state so sample buttons work
    if "_query_ta" not in st.session_state:
        st.session_state["_query_ta"] = st.session_state.query_input

    query = st.text_area(
        "Enter your business question",
        height=120,
        placeholder="e.g. What was total revenue in Q4 2023?",
        key="_query_ta",
    )
    # Keep query_input in sync when user types
    st.session_state.query_input = query

    col_btn, col_uid = st.columns([2, 1])
    with col_uid:
        user_id = st.text_input("User ID", value="demo_user", key="uid")
    with col_btn:
        run = st.button("🚀 Run Query", type="primary", use_container_width=True)

    if run:
        if query.strip():
            with st.spinner("🤖 Orchestrating agents…"):
                resp = _call_api(query.strip(), user_id or "demo_user")
            if resp:
                st.session_state.last_response = resp
                st.session_state.query_input   = query
                st.session_state.history.insert(0, {"query": query, "response": resp})
                st.rerun()
        else:
            st.warning("Please enter a question.")

    if st.session_state.history:
        with st.expander(f"📜 Query History ({len(st.session_state.history)})"):
            for i, item in enumerate(st.session_state.history[:8]):
                lbl = item["query"][:60] + ("…" if len(item["query"]) > 60 else "")
                if st.button(f"↩ {lbl}", key=f"h_{i}_{item['query'][:10]}"):
                    st.session_state.last_response = item["response"]
                    st.session_state["_query_ta"]  = item["query"]
                    st.session_state.query_input   = item["query"]
                    st.rerun()


# ── Response panel ───────────────────────────────────────────────────────────

def _render_response_panel(resp: dict) -> None:
    expl = resp.get("explainability", {})

    # Policy violations / warnings
    for v in resp.get("policy_violations", []):
        st.error(f"🚫 Policy Violation: {v}")
    for w in resp.get("policy_warnings", []):
        st.warning(f"⚠️ Policy Warning: {w}")

    # ── Answer ──────────────────────────────────────────────────────────────
    is_feasible = expl.get("is_feasible", True)
    category    = expl.get("query_category", "")

    # Infeasibility banner (Doc2 #2)
    if not is_feasible:
        cat_label = category.replace("_", " ").title()
        st.warning(f"⚠️ **Query Assessment: {cat_label}** — {expl.get('feasibility_reason', '')}")

    st.subheader("💬 Answer")
    st.markdown(resp.get("answer", "_No answer generated._"))

    # ── KPI row ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    conf    = resp.get("confidence_score", 0)
    r_score = expl.get("readiness_score", 1.0)
    r_label = expl.get("readiness_label", "")
    ai = expl.get("ai_decision") or {}
    actual_cost = resp.get("total_cost_usd", 0)
    estimated_cost = ai.get("selected_estimated_cost_usd", actual_cost)
    baseline_cost = ai.get("highest_estimated_cost_usd", estimated_cost)
    savings = max(0.0, (baseline_cost - actual_cost) / baseline_cost) if baseline_cost else 0.0
    agent_names = []
    for step in expl.get("agent_timeline", []):
        agent_name = step.get("agent_name", "")
        if agent_name in INFRA_STEPS or not agent_name:
            continue
        label = agent_name.replace("_", " ").title()
        if label not in agent_names:
            agent_names.append(label)
    agents_label = ", ".join(agent_names[:4])
    if len(agent_names) > 4:
        agents_label += ", ..."
    c1.metric("Confidence", f"{conf:.0%}")
    c1.progress(conf)
    c2.metric("Readiness", f"{r_score:.0%}", help=r_label)
    c2.progress(r_score)
    c3.metric("Latency", f"{resp.get('total_latency_ms', 0):.0f} ms")
    c4.metric("Tokens", f"{resp.get('total_tokens', 0):,}")
    c5.metric("Cost", f"Est. ${estimated_cost:.3f}", help=f"Actual: ${actual_cost:.3f} | Savings: {savings:.0%}")
    c6.metric("Agents Run", f"{len(agent_names)} Agents", help=agents_label or None)

    # ── Knowledge Coverage Score (Signature) ──────────────────────────────────
    _render_knowledge_coverage(expl)

    # ── Evidence Availability Dashboard (Doc2 #8) ────────────────────────────
    _render_evidence_availability(expl)

    # ── SQL results ─────────────────────────────────────────────────────────
    data = resp.get("data_results")
    if data and data.get("row_count", 0) > 0:
        with st.expander(
            f"📊 SQL Results — {data['row_count']} row(s) "
            f"in {data.get('execution_time_ms', 0):.1f} ms",
            expanded=True,
        ):
            import pandas as pd
            st.code(expl.get("sql_generated", ""), language="sql")
            st.dataframe(
                pd.DataFrame(data["rows"], columns=data["columns"]),
                use_container_width=True,
            )

    # ── Enterprise Readiness Score (Doc2 #11) ────────────────────────────────
    _render_readiness_score(expl)

    # ── Enterprise Observability (Enhancement #14) ───────────────────────────
    _render_observability(expl)

    # ── Execution Graph (Enhancement #13) ────────────────────────────────────
    _render_execution_graph(expl)

    # ── Evidence Summary (Enhancement #10) ───────────────────────────────────
    _render_evidence_summary(expl)

    # ── Cost Optimization (Enhancement #5) ───────────────────────────────────
    _render_cost_optimization(expl)

    # ── RAG passages ─────────────────────────────────────────────────────────
    passages = resp.get("rag_passages", [])
    if passages:
        with st.expander(
            f"📄 Document Evidence — {len(passages)} passage(s)",
            expanded=False,
        ):
            for i, p in enumerate(passages, 1):
                src = p.get("source", "?")
                if p.get("page"):
                    src += f" p.{p['page']}"
                st.markdown(f"**[{i}] {src}** — relevance `{p.get('score', 0):.3f}`")
                st.caption(p.get("text", "")[:500])
                st.divider()


# ── Doc2 Signature: Knowledge Coverage Score ─────────────────────────────────

def _render_knowledge_coverage(expl: dict) -> None:
    kc = expl.get("knowledge_coverage", {})
    if not kc:
        return
    sources     = kc.get("sources", [])
    overall_pct = kc.get("overall_pct", 0)
    rec         = kc.get("recommendation", "")
    avail       = kc.get("available", 0)
    total       = kc.get("total", 0)
    title       = kc.get("title", "Enterprise Knowledge Map")

    with st.expander(
        f"🗂️ {title} — {overall_pct}% ({avail}/{total} sources)",
        expanded=True,
    ):
        # Progress bar
        color = "#276749" if overall_pct >= 70 else ("#d97706" if overall_pct >= 40 else "#c53030")
        st.markdown(
            f'<div style="background:#e5e7eb;border-radius:6px;height:12px;overflow:hidden">'
            f'<div style="background:{color};width:{overall_pct}%;height:100%;border-radius:6px"></div>'
            f'</div><p style="color:{color};font-weight:700;margin:4px 0 10px">'
            f'{overall_pct}% Overall Coverage</p>',
            unsafe_allow_html=True,
        )

        # Per-source grid
        cols = st.columns(min(len(sources), 4))
        for i, src in enumerate(sources):
            icon    = src.get("icon", "📂")
            name    = src.get("name", "?")
            avail_s = src.get("available", False)
            badge   = "✅" if avail_s else "❌"
            bg      = "#f0fff4" if avail_s else "#fff5f5"
            border  = "#c6f6d5" if avail_s else "#fed7d7"
            cols[i % 4].markdown(
                f'<div style="background:{bg};border:1px solid {border};border-radius:6px;'
                f'padding:8px 10px;margin-bottom:6px;text-align:center">'
                f'<div style="font-size:1.2rem">{icon}</div>'
                f'<div style="font-size:0.75rem;font-weight:600;margin-top:2px">{name}</div>'
                f'<div style="font-size:1rem;margin-top:2px">{badge}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if rec:
            st.info(f"💡 {rec}")


# ── Doc2 #8: Evidence Availability Dashboard ─────────────────────────────────

def _render_evidence_availability(expl: dict) -> None:
    required  = expl.get("required_evidence", [])
    available = expl.get("available_evidence", [])
    missing   = expl.get("missing_evidence", [])

    if not required:
        return

    with st.expander(
        f"🔍 Evidence Availability — {len(available)}/{len(required)} available",
        expanded=True,
    ):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**📋 Required Evidence**")
            for item in required:
                found = item in available
                st.markdown(f"{'✅' if found else '❌'} {item}")

        with c2:
            st.markdown("**✅ Available Evidence**")
            if available:
                for item in available:
                    st.markdown(f"🟢 {item}")
            else:
                st.caption("_None found_")

        with c3:
            st.markdown("**❌ Missing Evidence**")
            if missing:
                possible_locations = expl.get("possible_evidence_locations", [])
                for item in missing:
                    st.markdown(f"🔴 {item}")
                if possible_locations:
                    st.markdown("**Possible Locations**")
                    for location in possible_locations:
                        st.markdown(f"• {location}")
            else:
                st.success("All evidence available")

        # Connector suggestions (Doc2 #6)
        conn = expl.get("connector_suggestions", [])
        if conn:
            st.markdown("---")
            st.markdown("**🔌 Suggested Enterprise Connectors**")
            conn_cols = st.columns(min(len(conn), 3))
            for i, c in enumerate(conn):
                conn_cols[i % 3].markdown(
                    f'<div style="background:#f0f4ff;border:1px solid #c3dafe;border-radius:6px;'
                    f'padding:8px 10px;margin-bottom:4px">'
                    f'<b>{c.get("name","")}</b> <span style="color:#553c9a;font-size:0.75rem">'
                    f'[{c.get("type","")}]</span><br>'
                    f'<span style="font-size:0.78rem;color:#57606a">{c.get("use_case","")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── Doc2 #11: Enterprise Readiness Score ─────────────────────────────────────

def _render_readiness_score(expl: dict) -> None:
    r_score      = expl.get("readiness_score", 1.0)
    r_label      = expl.get("readiness_label", "")
    skipped      = expl.get("skipped_stages", [])
    acq_recs     = expl.get("data_acquisition_recs", [])
    failure_cat  = expl.get("failure_category", "none") or "none"
    recs         = expl.get("recommendations", [])
    is_feasible  = expl.get("is_feasible", True)

    title = f"🏆 Enterprise Readiness — {r_label} ({r_score:.0%})"
    with st.expander(title, expanded=not is_feasible):
        c1, c2 = st.columns(2)
        clr = "#276749" if r_score >= 0.85 else ("#d97706" if r_score >= 0.50 else "#c53030")
        c1.markdown(f"**Score:** <span style='color:{clr};font-size:1.2rem;font-weight:700'>{r_score:.0%}</span>", unsafe_allow_html=True)
        c1.progress(r_score)
        c1.markdown(f"**Status:** `{r_label}`")

        if failure_cat and failure_cat != "none":
            FAILURE_ICONS = {
                "no_data":           "🗃️ No Data Found",
                "insufficient_data": "📂 Insufficient Data",
                "connector_offline": "🔌 Connector Offline",
                "llm_failure":       "🤖 LLM Failure",
                "sql_failure":       "⚙️ SQL Failure",
                "db_timeout":        "⏱️ Database Timeout",
                "rag_failure":       "🔎 RAG Failure",
                "partial_evidence":  "⚠️ Partial Evidence",
                "permission_denied": "🔐 Permission Denied",
            }
            c2.markdown(f"**Failure Category:**")
            c2.error(FAILURE_ICONS.get(failure_cat, f"⚠️ {failure_cat}"))

        if recs:
            st.markdown("**Recommendations**")
            for r in recs:
                st.markdown(f"  ✓ {r}")

        if acq_recs:
            st.markdown("**Data Acquisition Recommendations**")
            for a in acq_recs:
                st.markdown(f"  → {a}")

        if skipped:
            with st.expander(f"⏭️ Skipped Pipeline Stages ({len(skipped)})"):
                import pandas as pd
                df = pd.DataFrame(skipped)
                df.columns = ["Stage", "Reason"]
                st.dataframe(df, use_container_width=True, hide_index=True)




# ── Enhancement #14 — Enterprise Observability ───────────────────────────────

def _render_observability(expl: dict) -> None:
    timeline   = expl.get("agent_timeline", [])
    agent_steps = [s for s in timeline if s["agent_name"] not in INFRA_STEPS]

    with st.expander("📡 Enterprise Observability Dashboard", expanded=False):
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Latency",    f"{expl.get('total_latency_ms', 0):.0f} ms")
        c2.metric("LLM Calls",        expl.get("llm_call_count", 0))
        c3.metric("DB Calls",         expl.get("db_call_count", 0))
        c4.metric("Doc Retrievals",   expl.get("doc_retrieval_count", 0))
        c5.metric("Tokens Used",      f"{expl.get('total_tokens', 0):,}")
        c6.metric("Est. AI Cost",     f"${expl.get('total_cost_usd', 0):.4f}")

        if agent_steps:
            import pandas as pd
            st.markdown("**Agent Execution Breakdown**")
            df = pd.DataFrame([{
                "Agent":      s["agent_name"],
                "Status":     s["status"].upper(),
                "Time (ms)":  round(s.get("duration_ms", 0), 1),
                "Summary":    s.get("output_summary", "")[:70],
            } for s in agent_steps])
            st.dataframe(df, use_container_width=True, hide_index=True)


# ── Enhancement #13 — Execution Graph (SVG, top-down, colour-coded) ──────────

def _render_execution_graph(expl: dict) -> None:
    timeline = expl.get("agent_timeline", [])
    if not timeline:
        return

    with st.expander("🗺️ Execution Pipeline Graph", expanded=False):
        # Legend
        leg_cols = st.columns(6)
        legend = [
            ("#553c9a", "#e9d8fd", "Infrastructure"),
            ("#276749", "#c6f6d5", "AI Agent"),
            ("#7b341e", "#feebc8", "Data Layer"),
            ("#1a365d", "#bee3f8", "Planner"),
            ("#2d3748", "#e2e8f0", "Synthesis"),
            ("#9b2c2c", "#fed7d7", "Error"),
        ]
        for i, (bc, fc, label) in enumerate(legend):
            leg_cols[i].markdown(
                f'<span style="background:{fc};border:1.5px solid {bc};'
                f'padding:2px 8px;border-radius:4px;font-size:0.75rem">{label}</span>',
                unsafe_allow_html=True,
            )

        st.markdown("")

        # SVG parameters
        NODE_W, NODE_H = 180, 44
        GAP_X, GAP_Y   = 20, 16
        COLS            = 4
        nodes           = timeline
        n               = len(nodes)
        rows            = (n + COLS - 1) // COLS
        svg_w           = COLS * (NODE_W + GAP_X) + GAP_X
        svg_h           = rows * (NODE_H + GAP_Y) + GAP_Y + 50

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
            f'style="font-family:-apple-system,Segoe UI,sans-serif;background:#f7f8fa;'
            f'border-radius:10px;border:1px solid #e5e7eb">',
            f'<text x="{svg_w//2}" y="26" text-anchor="middle" font-size="13" '
            f'font-weight="700" fill="#1a365d">EIO Execution Pipeline</text>',
            '<defs>'
            '<marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
            '<path d="M0,0 L0,6 L8,3 z" fill="#94a3b8"/></marker>'
            '</defs>',
        ]

        for i, step in enumerate(nodes):
            col_i = i % COLS
            row_i = i // COLS
            x = GAP_X + col_i * (NODE_W + GAP_X)
            y = 38 + GAP_Y + row_i * (NODE_H + GAP_Y)

            name   = step.get("agent_name", "?")
            status = step.get("status", "success")
            dur    = step.get("duration_ms", 0)
            icon   = AGENT_ICONS.get(name, "🔧")
            label  = name[:22]

            # Determine node colour
            if status == "error":
                bc, fc = "#9b2c2c", "#fed7d7"
            else:
                ntype = _NODE_TYPE.get(name, "agent")
                bc, fc = _NODE_COLORS.get(ntype, ("#276749", "#c6f6d5"))

            # Node box
            parts.append(
                f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" '
                f'rx="7" fill="{fc}" stroke="{bc}" stroke-width="1.8"/>'
            )
            # Step index badge
            parts.append(
                f'<circle cx="{x+14}" cy="{y+14}" r="9" fill="{bc}"/>'
                f'<text x="{x+14}" y="{y+18}" text-anchor="middle" '
                f'font-size="9" font-weight="700" fill="white">{i+1}</text>'
            )
            # Label
            parts.append(
                f'<text x="{x+28}" y="{y+16}" font-size="11" font-weight="600" fill="#1f2328">'
                f'{label}</text>'
            )
            # Duration
            parts.append(
                f'<text x="{x+28}" y="{y+32}" font-size="9" fill="#57606a">'
                f'{dur:.0f} ms  {STATUS_COLORS.get(status,"⚪")}</text>'
            )

            # Arrow — right if same row, down if last in row
            if i + 1 < n:
                nx_col = (i + 1) % COLS
                nx_row = (i + 1) // COLS
                if nx_row == row_i:
                    # horizontal arrow →
                    ax1 = x + NODE_W; ay1 = y + NODE_H // 2
                    ax2 = ax1 + GAP_X; ay2 = ay1
                    parts.append(
                        f'<line x1="{ax1}" y1="{ay1}" x2="{ax2}" y2="{ay2}" '
                        f'stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arr)"/>'
                    )
                else:
                    # bend arrow: down from last in row, then left to start of next row
                    bx1 = x + NODE_W // 2; by1 = y + NODE_H
                    bx2 = bx1;              by2 = by1 + GAP_Y // 2
                    bx3 = GAP_X + NODE_W // 2; by3 = by2
                    bx4 = bx3;                 by4 = by2 + GAP_Y // 2
                    parts.append(
                        f'<polyline points="{bx1},{by1} {bx2},{by2} {bx3},{by3} {bx4},{by4}" '
                        f'fill="none" stroke="#94a3b8" stroke-width="1.5" '
                        f'stroke-dasharray="4,3" marker-end="url(#arr)"/>'
                    )

        parts.append("</svg>")
        st.markdown("\n".join(parts), unsafe_allow_html=True)


# ── Enhancement #10 — Evidence Summary ──────────────────────────────────────

def _render_evidence_summary(expl: dict) -> None:
    sources    = expl.get("evidence_sources", [])
    rd         = expl.get("routing_decision") or {}
    ai         = expl.get("ai_decision") or {}
    model_name = ai.get("selected_display_name") or rd.get("model", "")
    conf       = expl.get("confidence_score", 0)
    breakdown  = (expl.get("governance") or {}).get("confidence_breakdown", {})

    with st.expander("🧾 Evidence Summary & Confidence", expanded=True):
        ALL_SOURCES = [
            ("Database",        "🗄️"),
            ("Documents",       "📄"),
            ("Metadata",        "🔍"),
            ("Business Glossary","📖"),
            ("Data Quality",    "📊"),
            ("Data Lineage",    "🔗"),
        ]
        cols = st.columns(3)
        for i, (src, icon) in enumerate(ALL_SOURCES):
            used = src in sources
            badge = "✅" if used else "⬜"
            cols[i % 3].markdown(
                f'{badge} {icon} **{src}**',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        c1, c2 = st.columns(2)
        if model_name:
            c1.markdown(f"**Reasoning Model**\n\n`{model_name}`")
        c2.markdown("**Confidence Score**")
        c2.progress(conf, text=f"{conf:.0%}")

        if breakdown:
            st.markdown("**Confidence Breakdown**")
            b1, b2, b3, b4, b5 = st.columns(5)
            b1.metric("Evidence", f"{breakdown.get('evidence', 0):.0%}")
            b2.metric("Planner", f"{breakdown.get('planner', 0):.0%}")
            b3.metric("Metadata", f"{breakdown.get('metadata', 0):.0%}")
            b4.metric("Knowledge Coverage", f"{breakdown.get('knowledge_coverage', 0):.0%}")
            b5.metric("Final", f"{breakdown.get('final', 0):.0%}")


# ── Enhancement #5 — Cost Optimization Engine ────────────────────────────────

def _render_cost_optimization(expl: dict) -> None:
    ai = expl.get("ai_decision") or {}
    candidates = ai.get("candidates_evaluated", [])
    if not candidates:
        return

    with st.expander("💰 Cost Optimization Engine", expanded=False):
        st.caption(
            "EIO evaluates every registered model on cost, latency, accuracy, and "
            "governance before selecting the optimal model for this request."
        )
        import pandas as pd
        actual_cost = expl.get("total_cost_usd", 0)
        estimated_cost = ai.get("selected_estimated_cost_usd", actual_cost)

        eligible = [c for c in candidates if not c.get("disqualified")]
        disq     = [c for c in candidates if c.get("disqualified")]

        rows = []
        for c in sorted(eligible, key=lambda x: -x.get("total_score", 0)):
            sc = c.get("scores", {})
            cost_1k = c.get("cost_per_1k_in", 0)
            est_cost = cost_1k * ai.get("estimated_tokens", 0) / 1000
            rows.append({
                "Model":        c.get("display_name", ""),
                "Provider":     c.get("provider", "").upper(),
                "Score":        f"{c.get('total_score', 0):.1f}/100",
                "Reasoning":    f"{sc.get('reasoning', 0):.0f}",
                "SQL":          f"{sc.get('sql', 0):.0f}",
                "Context":      f"{sc.get('long_context', 0):.0f}",
                "Gov":          f"{sc.get('governance', 0):.0f}",
                "Cost Eff":     f"{sc.get('cost', 0):.0f}",
                "Latency":      f"{sc.get('latency', 0):.0f}",
                "Est. Cost $":  f"{est_cost:.5f}",
                "Avg ms":       c.get("avg_latency_ms", 0),
                "Notes":        c.get("notes", "")[:45],
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Winner summary
        winner = sorted(eligible, key=lambda x: -x.get("total_score", 0))[0] if eligible else None
        if winner:
            baseline = max(
                [((c.get("cost_per_1k_in", 0) * ai.get("estimated_tokens", 0)) / 1000) for c in eligible],
                default=estimated_cost,
            )
            savings = max(0.0, (baseline - actual_cost) / baseline) if baseline else 0.0
            st.markdown(
                f"**✅ Recommended:** `{winner.get('display_name')}` "
                f"(score {winner.get('total_score',0):.1f}/100)"
            )
            s1, s2, s3 = st.columns(3)
            s1.metric("Estimated", f"${estimated_cost:.3f}")
            s2.metric("Actual", f"${actual_cost:.3f}")
            s3.metric("Savings", f"{savings:.0%}", help="Compared to the highest estimated cost candidate")
            st.caption(ai.get("selection_reason", "")[:250])

        # Disqualified
        if disq:
            with st.expander(f"❌ Disqualified Models ({len(disq)})"):
                for c in disq:
                    st.caption(f"• **{c.get('display_name')}**: {c.get('disqualify_reason', '')}")


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR (4 tabs)
# ════════════════════════════════════════════════════════════════════════════

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🔎 Explainability")
        resp = st.session_state.last_response
        if not resp:
            st.info("Run a query to see the full execution trace.")
            _sidebar_registry_preview()
            _render_platform_info()
            return

        expl = resp.get("explainability", {})
        tab1, tab2, tab3, tab4 = st.tabs(["🧠 Planner", "⚡ AI Engine", "🛡️ Gov", "📋 Timeline"])

        with tab1:
            _sidebar_planner(expl)
        with tab2:
            _sidebar_ai_engine(expl)
        with tab3:
            _sidebar_governance(expl)
        with tab4:
            _sidebar_timeline(expl)

        st.divider()
        _render_platform_info()


# ── Sidebar: platform info ───────────────────────────────────────────────────

def _sidebar_registry_preview() -> None:
    """Show model health registry in sidebar before first query."""
    health_data = _safe_get(MHEALTH_EP) or {}
    entries = health_data.get("entries", [])
    if not entries:
        return
    st.markdown("**💓 Model Health Registry**")
    for e in entries[:6]:
        status = e.get("status", "unknown")
        icon   = "🟢" if status == "online" else ("🟡" if status == "degraded" else ("🔴" if status == "offline" else "⚪"))
        st.markdown(
            f'{icon} `{e.get("display_name","?")[:22]}` '
            f'<span style="color:#57606a;font-size:0.75rem">{e.get("avg_latency_ms",0):.0f}ms</span>',
            unsafe_allow_html=True,
        )


def _render_platform_info() -> None:
    st.markdown("**🏗️ Platform**")
    cfg = _safe_get(CONFIG_EP) or {}
    h   = _safe_get(HEALTH_EP) or {}
    conns = h.get("connectors", {})
    for name, status in conns.items():
        s  = status.get("status", "?")
        ic = "🟢" if s == "ok" else ("🟡" if s == "stub" else "🔴")
        st.caption(f"{ic} {name.upper()}: {s}")
    st.caption(f"DB connectors:      {len(cfg.get('available_db_connectors', []))}")
    st.caption(f"Storage connectors: {len(cfg.get('available_storage_connectors', []))}")
    st.caption(f"LLM providers:      {len(cfg.get('available_llm_providers', []))}")


# ── Sidebar Tab 1: Planner Dashboard (Enhancement #2) ────────────────────────

def _sidebar_planner(expl: dict) -> None:
    st.markdown("#### 🧠 Planner Reasoning Dashboard")

    # ── Doc2 #1: Query classification ────────────────────────────────────────
    category    = expl.get("query_category", "")
    is_feasible = expl.get("is_feasible", True)
    intent      = expl.get("planner_intent", "")
    strategy    = expl.get("planner_execution_strategy", "")
    skills      = expl.get("planner_skills", [])
    tools       = expl.get("planner_tools", [])
    entities    = expl.get("detected_entities", [])
    reasoning   = expl.get("planner_reasoning", "")
    cost_exp    = expl.get("estimated_cost_explanation", "")
    r_score     = expl.get("readiness_score", 1.0)
    r_label     = expl.get("readiness_label", "")

    # Query category badge
    if category:
        CAT_COLORS = {
            "database":          ("#276749", "#c6f6d5"),
            "document":          ("#2c5282", "#bee3f8"),
            "hybrid":            ("#553c9a", "#e9d8fd"),
            "metadata":          ("#7b341e", "#feebc8"),
            "glossary":          ("#2d3748", "#e2e8f0"),
            "general":           ("#1a365d", "#bee3f8"),
            "unsupported":       ("#9b2c2c", "#fed7d7"),
            "insufficient_data": ("#c05621", "#feebc8"),
        }
        bc, fc = CAT_COLORS.get(category, ("#2d3748", "#e2e8f0"))
        feasible_badge = "✅ Feasible" if is_feasible else "❌ Infeasible"
        st.markdown(
            f'<span style="background:{fc};border:1.5px solid {bc};padding:3px 10px;'
            f'border-radius:4px;font-size:0.8rem;font-weight:700">'
            f'{category.replace("_"," ").title()}</span>'
            f'&nbsp;&nbsp;<span style="font-size:0.8rem">{feasible_badge}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("")

    # Feasibility reason
    feas_reason = expl.get("feasibility_reason", "")
    if feas_reason:
        if is_feasible:
            st.success(f"✅ {feas_reason[:200]}")
        else:
            st.error(f"❌ {feas_reason[:200]}")

    # Business intent
    if intent:
        st.markdown("**Business Intent**")
        st.info(intent[:250])

    # Detected entities
    if entities:
        st.markdown("**Detected Entities**")
        st.markdown("  ".join(f"`{e}`" for e in entities))

    # Execution strategy
    if strategy:
        strat_icon = {
            "Database Only":               "🗄️",
            "Documents Only":              "📄",
            "Hybrid Database + Documents": "🔀",
            "Multi-Agent Workflow":        "🤖",
        }.get(strategy, "⚙️")
        st.markdown(f"**Execution Strategy:** {strat_icon} `{strategy}`")

    if skills:
        st.markdown("**Required Skills**")
        for sk in skills:
            st.markdown(f"&nbsp;&nbsp;✓ {sk}")

    if tools:
        st.markdown("**Enterprise Tools**")
        for t in tools:
            st.markdown(f"&nbsp;&nbsp;🔧 {t}")

    # Readiness score
    st.markdown("---")
    clr = "#276749" if r_score >= 0.85 else ("#d97706" if r_score >= 0.50 else "#c53030")
    st.markdown(f"**Enterprise Readiness:** <span style='color:{clr};font-weight:700'>{r_score:.0%} — {r_label}</span>", unsafe_allow_html=True)
    st.progress(r_score)

    # Planner full reasoning
    if reasoning:
        st.markdown("---")
        st.markdown("**Planner Reasoning**")
        st.caption(reasoning[:400])

    if cost_exp:
        st.markdown("**Cost Estimate Reason**")
        st.caption(cost_exp[:200])

    # ── Enhancement #8: DB execution details ─────────────────────────────────
    st.markdown("---")
    st.markdown("**🗄️ Database Execution**")
    st.markdown(f"Connector: `{expl.get('db_connector_type', 'SQLiteConnector')}`")
    st.markdown(f"Rows returned: **{expl.get('db_rows_returned', 0)}**")
    st.markdown(f"Execution time: **{expl.get('db_execution_time_ms', 0):.1f} ms**")
    cache = expl.get("db_cache_hit", False)
    st.markdown(f"Cache: {'✅ Hit' if cache else '🔄 Miss'}")

    # ── Enhancement #9: Knowledge retrieval ──────────────────────────────────
    st.markdown("---")
    st.markdown("**🔎 Knowledge Retrieval**")
    st.markdown(f"Storage: `{expl.get('storage_provider', 'LocalFileSystemConnector')}`")
    st.markdown(f"Vector DB: `{expl.get('vector_db', 'chromadb')}`")
    docs     = expl.get("documents_retrieved", [])
    passages = expl.get("rag_passages", [])
    st.markdown(f"Documents retrieved: **{len(docs)}**")
    st.markdown(f"Passages retrieved: **{len(passages)}**")
    if passages:
        avg_sc = sum(p.get("score", 0) for p in passages) / len(passages)
        st.markdown(f"Retrieval confidence: **{avg_sc:.3f}**")
    rag_ms = expl.get("rag_retrieval_time_ms", 0)
    st.markdown(f"Retrieval time: **{rag_ms:.0f} ms**")


# ── Sidebar Tab 2: AI Decision Engine (Enhancements #1, #3, #4, #5, #6) ─────

def _sidebar_ai_engine(expl: dict) -> None:
    ai = expl.get("ai_decision") or {}

    if not ai:
        st.info("No AI Decision Engine data.")
        return

    st.markdown("#### ⚡ AI Decision Engine")

    # Request summary
    c1, c2 = st.columns(2)
    c1.metric("Complexity",   ai.get("request_complexity", "—").title())
    c2.metric("Est. Tokens",  f"{ai.get('estimated_tokens', 0):,}")
    st.metric("Est. Cost",    f"${ai.get('estimated_cost_usd', 0):.4f}")

    caps = ai.get("required_capabilities", [])
    if caps:
        st.markdown("**Required Capabilities**")
        st.markdown("  ".join(f"`{c}`" for c in caps))

    # ── Winner card ───────────────────────────────────────────────────────────
    st.markdown("---")
    sel  = ai.get("selected_display_name", "")
    sc   = ai.get("selection_confidence", 0)
    reason = ai.get("selection_reason", "")
    st.markdown(f"**🏆 Selected Model:** `{sel}`")
    st.progress(min(sc / 100, 1.0), text=f"Confidence: {sc:.1f}/100")
    if reason:
        st.caption(reason[:200])

    policies = ai.get("policy_applied", [])
    if policies:
        st.markdown("**Policies Applied**")
        for p in policies:
            st.caption(f"🛡️ {p.replace('_', ' ').title()}")

    # ── Candidate Evaluation Matrix (Enhancement #1, #5) ─────────────────────
    candidates = ai.get("candidates_evaluated", [])
    if candidates:
        st.markdown("---")
        st.markdown("**📊 Candidate Scoring Matrix** *(7 Dimensions)*")

        eligible = [c for c in candidates if not c.get("disqualified")]
        disq     = [c for c in candidates if c.get("disqualified")]

        for c in sorted(eligible, key=lambda x: -x.get("total_score", 0)):
            sc_dict = c.get("scores", {})
            is_winner = c.get("display_name") == sel
            prefix = "🏆 " if is_winner else ""
            with st.container():
                name_col, score_col = st.columns([3, 1])
                name_col.markdown(f"**{prefix}{c.get('display_name', '')}**")
                score_col.markdown(f"`{c.get('total_score', 0):.1f}`")
                st.progress(c.get("total_score", 0) / 100)
                # 7 dimension mini-bars
                dm_cols = st.columns(7)
                dims = [
                    ("Reason", "reasoning"),
                    ("SQL",    "sql"),
                    ("LongCtx","long_context"),
                    ("Gov",    "governance"),
                    ("Cost",   "cost"),
                    ("Latency","latency"),
                ]
                for i, (dim_label, dim_key) in enumerate(dims):
                    val = sc_dict.get(dim_key, 0)
                    dm_cols[i].markdown(
                        f'<div style="font-size:0.65rem;text-align:center;color:#57606a">{dim_label}</div>'
                        f'<div style="font-size:0.8rem;font-weight:700;text-align:center">{val:.0f}</div>',
                        unsafe_allow_html=True,
                    )
                cost_display = (
                    f"${c.get('cost_per_1k_in', 0):.4f}/1k"
                    if c.get("cost_per_1k_in", 0) > 0 else "Free"
                )
                caps_tags = " · ".join(c.get("capabilities", [])[:4])
                st.caption(f"Cost: {cost_display} · Avg: {c.get('avg_latency_ms', 0):.0f}ms · {caps_tags}")
                st.markdown("")

        if disq:
            with st.expander(f"❌ Disqualified ({len(disq)})"):
                for c in disq:
                    st.caption(f"• **{c.get('display_name')}**: {c.get('disqualify_reason', '')}")

    # ── Enhancement #3: Model Capability Registry ─────────────────────────────
    st.markdown("---")
    st.markdown("**📋 Model Capability Registry** *(Enhancement #3)*")
    models_data = _safe_get(MODELS_EP) or {}
    profiles    = models_data.get("profiles", [])
    if profiles:
        for p in profiles[:4]:
            caps = p.get("capabilities", [])
            st.caption(
                f"**{p.get('display_name','')}** — "
                f"{', '.join(caps[:3])}{'…' if len(caps) > 3 else ''} · "
                f"${p.get('cost_per_1k_input',0):.4f}/1k"
            )

    # ── Enhancement #4: Model Health Registry ─────────────────────────────────
    st.markdown("---")
    st.markdown("**💓 Model Health Registry** *(Enhancement #4)*")
    health_data = _safe_get(MHEALTH_EP) or {}
    entries     = health_data.get("entries", [])
    if entries:
        for e in entries:
            status = e.get("status", "unknown")
            icon   = "🟢" if status == "online" else ("🟡" if status == "degraded" else ("🔴" if status == "offline" else "⚪"))
            label  = e.get("health_label", "Unknown")
            avg_ms = e.get("avg_latency_ms", 0)
            last   = e.get("last_success", "Never")
            if last and last != "Never":
                last = last[:10]
            st.markdown(
                f'{icon} **{e.get("display_name","?")}**  '
                f'<span style="color:#57606a;font-size:0.75rem">'
                f'{label} · {avg_ms:.0f}ms · last: {last}</span>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No health data (run a query to populate)")

    # ── Enhancement #6: Task-Level Model Routing ──────────────────────────────
    task_assignments = ai.get("task_assignments", [])
    if task_assignments:
        st.markdown("---")
        st.markdown("**🔀 Task-Level Model Routing** *(Enhancement #6)*")
        st.caption("Different models handle different pipeline stages:")
        for i, t in enumerate(task_assignments):
            stage  = t.get("stage", "").replace("_", " ").title()
            dname  = t.get("display_name", "")
            prov   = t.get("provider", "").upper()
            reason = t.get("reason", "")
            connector = "─" if i == 0 else "↓"
            st.markdown(
                f'{connector} **{stage}**  \n'
                f'&nbsp;&nbsp;&nbsp;`{dname}` ({prov})',
            )
            st.caption(f"&nbsp;&nbsp;&nbsp;{reason[:80]}")


# ── Sidebar Tab 3: Governance (Enhancements #11, #12) ────────────────────────

def _sidebar_governance(expl: dict) -> None:
    gov = expl.get("governance", {})
    uc  = expl.get("user_context", {})

    st.markdown("#### 🛡️ Governance Dashboard")

    if gov.get("simulation_mode"):
        st.warning("ℹ️ Simulation Mode — enterprise IDP not yet connected")

    # Authentication (Enhancement #11)
    auth = gov.get("authentication", {})
    st.markdown("**Authentication**")
    status_ok = "Authenticated" in auth.get("status", "")
    st.markdown(f"{'✅' if status_ok else '❌'} {auth.get('status', 'Unknown')}")
    st.markdown(
        f"Method: `{auth.get('method','demo')}` · "
        f"Provider: `{auth.get('provider','simulation')}`"
    )
    st.markdown(f"MFA: {'✅ Verified' if auth.get('mfa_verified') else '⬜ Not verified'}")

    # Authorization / RBAC (Enhancement #12)
    st.markdown("---")
    st.markdown("**Authorization (RBAC/ABAC)**")
    st.markdown(f"User ID: `{uc.get('user_id','anon')}`")
    roles_str = " · ".join(f"`{r}`" for r in uc.get("roles", []))
    st.markdown(f"Roles: {roles_str}")
    st.markdown(f"Department: `{uc.get('department','')}`")
    clearance = uc.get("clearance", "public")
    clevel = {"public": 1, "internal": 2, "confidential": 3, "restricted": 4}.get(clearance, 1)
    st.markdown(f"Clearance: `{clearance}`")
    st.progress(clevel / 4, text=f"Level {clevel}/4 — {clearance.title()}")

    # Policy Engine (Enhancement #11)
    st.markdown("---")
    st.markdown("**Policy Engine**")
    pe = gov.get("policy_engine", {})
    passed = pe.get("pre_check_passed", True)
    st.markdown(f"Pre-routing check: {'✅ Passed' if passed else '❌ Blocked'}")
    st.markdown(f"Data Classification: `{pe.get('data_classification','')}`")
    st.markdown(f"Selected Policy: `{pe.get('selected_policy','')}`")
    st.markdown(f"Model Approved: {'✅' if pe.get('approved_model') else '❌'}")

    viols = expl.get("policy_violations", [])
    warns = expl.get("policy_warnings", [])
    if viols:
        for v in viols:
            st.error(f"🚫 {v}")
    if warns:
        for w in warns:
            st.warning(f"⚠️ {w}")
    if not viols and not warns:
        st.success("No violations or warnings")

    # Future integrations
    st.markdown("---")
    st.markdown("**Future IDP Integrations**")
    for idp in gov.get("future_integrations", []):
        st.markdown(f"&nbsp;&nbsp;○ {idp}")


# ── Sidebar Tab 4: Timeline (Enhancement #7) ─────────────────────────────────

def _sidebar_timeline(expl: dict) -> None:
    timeline = expl.get("agent_timeline", [])
    if not timeline:
        st.info("No timeline data.")
        return

    st.markdown("#### 📋 Execution Timeline")

    # SQL
    sql = expl.get("sql_generated")
    if sql:
        validated = expl.get("sql_validated", False)
        st.markdown("**Generated SQL**")
        st.caption(f"Validation: {'✅ Passed' if validated else '❌ Failed'}")
        st.code(sql, language="sql")

    # Steps
    for i, step in enumerate(timeline, 1):
        name     = step.get("agent_name", "?")
        icon     = AGENT_ICONS.get(name, "🔧")
        sc       = STATUS_COLORS.get(step.get("status", "success"), "⚪")
        dur      = step.get("duration_ms", 0)
        is_infra = name in INFRA_STEPS

        bg     = "#f0f4ff" if is_infra else "#f7f8fa"
        border = "#553c9a" if is_infra else "#276749"
        if step.get("status") == "error":
            bg, border = "#fff5f5", "#c53030"

        st.markdown(
            f'<div style="background:{bg};border-left:3px solid {border};'
            f'padding:4px 8px;margin:3px 0;border-radius:0 4px 4px 0;font-size:0.82rem">'
            f'<span style="color:#718096;font-size:0.7rem">#{i}</span> '
            f'{sc} {icon} <b>{name}</b>'
            f'<span style="float:right;color:#718096">{dur:.0f} ms</span><br>'
            f'<span style="color:#4a5568;font-size:0.75rem">'
            f'{step.get("output_summary","")[:90]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Data quality
    dq = expl.get("data_quality")
    if dq:
        st.markdown("---")
        st.markdown("**Data Quality**")
        qs = dq.get("quality_score", 1.0)
        st.progress(qs, text=f"Quality Score: {qs:.0%}")
        for flag in dq.get("anomaly_flags", []):
            st.caption(f"⚠️ {flag}")

    # Lineage
    lineage = expl.get("lineage", [])
    if lineage:
        with st.expander(f"🔗 Data Lineage ({len(lineage)} entries)"):
            for e in lineage:
                st.caption(
                    f"**{e.get('source_type','?')}** · "
                    f"{e.get('source_name','?')} · "
                    f"`{e.get('operation','?')}`"
                )

    req_id = expl.get("request_id", "")
    if req_id:
        st.caption(f"Request ID: `{req_id[:12]}…`")


# ════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def _call_api(query: str, user_id: str = "demo_user") -> dict | None:
    try:
        r = requests.post(
            QUERY_EP,
            json={"user_query": query, "user_id": user_id},
            timeout=180,
        )
        if r.ok:
            return r.json()
        st.error(f"API error {r.status_code}: {r.text[:300]}")
    except requests.exceptions.ConnectionError:
        st.error(
            f"Cannot connect to EIO API at {API_URL}.\n\n"
            f"Start the API with:\n"
            f"```\nuvicorn eio.api.main:app --reload --port 8000\n```"
        )
    except Exception as exc:
        st.error(f"Request failed: {exc}")
    return None


def _safe_get(url: str, timeout: int = 4) -> dict | None:
    try:
        r = requests.get(url, timeout=timeout)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


# ── CSS ──────────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown("""
    <style>
    /* Header */
    .eio-header {
        background: linear-gradient(135deg, #1a365d 0%, #2d3748 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
    }
    .eio-header h1 { color: #fff; margin: 0; font-size: 1.75rem; }
    .eio-header p  { color: #a0aec0; margin: 0.3rem 0 0; font-size: 0.88rem; }

    /* Welcome card */
    .eio-welcome {
        background: #f7f8fa;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.5rem 1.8rem;
        margin-bottom: 1rem;
    }
    .eio-welcome h3 { color: #1a365d; margin: 0 0 0.5rem; }
    .eio-welcome p  { color: #4a5568; margin: 0; }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: #f7f8fa;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 8px 12px;
    }

    /* Sidebar compaction */
    section[data-testid="stSidebar"] { min-width: 340px; }

    /* Code blocks */
    .stCode { font-size: 0.8rem !important; }
    </style>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
