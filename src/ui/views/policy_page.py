import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_json, read_markdown
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.policy.service import generate_policy


def render():
    render_page_header(
        title_en="Stage 10 — Policy Output",
        title_fa="مرحله ۱۰ — خروجی استراتژی و سیاست‌های اجرایی",
        desc_en="This final synthesis translates raw algebraic decisions into human-readable policies. It applies priority thresholds and documents exact container routing orders and modal assignments.",
        desc_fa="این مرحله نتایج خام ریاضی را به دستورالعمل‌های اجرایی و قابل خواندن تبدیل می‌کند. مسیرها، اولویت‌بندی عملیات و اختصاص مدلهای ترابری مشخص شده و آماده اجرا در شبکه لجستیک می‌گردند."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("policy", fn=generate_policy, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_pol"):
            st.cache_data.clear()

    if dependency_warning("policy"):
        return

    artifact_panel(["final_policy.json", "final_policy_report.md"])

    data = read_json("final_policy.json")
    if data is None:
        st.info("Wait... Run the Policy Output stage above to synthesize the final plan.")
        return

    # ── Header KPIs ────────────────────────────────────────────────────────
    render_section_title("Execution Directives Summary")
    s = data.get("summary", {})
    kpi_row({
        "System Status":   data.get("policy_status", "—").upper(),
        "Architecture": data.get("selected_solver", "—"),
        "Total Operations":         str(len(data.get("actions", []))),
        "Total Volume Repositioned":       f"{s.get('total_repositioned_teu', 0):,.1f} TEU",
        "Total Incurred Cost":      f"${s.get('total_estimated_cost', 0):,.0f}",
        "Global Service Target":   f"{s.get('expected_service_level', 0):.1%}",
        "Critical Shortfall":    f"{s.get('remaining_unmet_demand_teu', 0):,.1f} TEU",
    })

    # ── Actions table ──────────────────────────────────────────────────────
    actions = data.get("actions", [])
    if actions:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_title("Operational Routing Orders (RO)")
        render_caption("Discrete physical relocation orders assigned by priority tier and modal availability.")
        df_act = pd.DataFrame(actions)
        priority_cols = ["action_id", "priority_level", "origin_port", "destination_port", "mode",
                         "quantity_teu", "estimated_cost", "departure_period_idx", "arrival_period_idx"]
        show_df(df_act[[c for c in priority_cols if c in df_act.columns]])

    # ── Explainability ─────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_title("Algorithmic Explainability & Notes")
    expl = data.get("explanation", {})
    tabs = st.tabs(["💡 Rationalization", "⚠️ Computational Limitations", "🚨 Operational Warnings", "↔️ Optimization Trade-offs"])
    with tabs[0]:
        st.markdown(expl.get("solver_selection_reason", "—"))
        st.markdown("---")
        st.markdown(expl.get("policy_description", "—"))
    with tabs[1]:
        lims = expl.get("limitations", [])
        for l in lims:
            st.warning(l)
        if not lims:
            st.success("No logical limitations flagged during compilation.")
    with tabs[2]:
        warns = expl.get("warnings", [])
        for w in warns:
            st.error(w)
        if not warns:
            st.success("No critical warnings emitted from solver.")
    with tabs[3]:
        for t in expl.get("trade_offs_accepted", []):
            st.info(t)

    # ── Markdown report ────────────────────────────────────────────────────
    md = read_markdown("final_policy_report.md")
    if md:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_title("Automated Post-Ops Overview")
        with st.expander("📄 View Full Markdown Dispatch Report", expanded=False):
            st.markdown(md)
