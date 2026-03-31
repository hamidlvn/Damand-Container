import streamlit as st
from src.ui.utils import load_config, read_json
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import kpi_row
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.solver_selection.service import select_solver


def render():
    render_page_header(
        title_en="Stage 7 — Solver Selection",
        title_fa="مرحله ۷ — انتخاب موتور بهینه‌سازی",
        desc_en="This rule-based engine evaluates structural complexity (nodes, periods, arcs) against computational thresholds. It dynamically routes the problem to the exact algebraic or heuristic solver strictly best suited for the mathematical scale.",
        desc_fa="این موتور هوشمند، پیچیدگی ساختاری مسئله را (بر اساس تعداد گره‌ها، مسافت‌ها و زمان) ارزیابی کرده و مناسب‌ترین الگوریتم بهینه‌سازی (ابتکاری یا دقیق خطی) را برای اجرا با بالاترین بهره‌وری انتخاب می‌کند."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("solver_selection", fn=select_solver, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_ss"):
            st.cache_data.clear()

    if dependency_warning("solver_selection"):
        return

    artifact_panel(["solver_strategy.json"])

    data = read_json("solver_strategy.json")
    if data is None:
        st.info("Wait... Run the Solver Selection stage above to query the decision matrix.")
        return

    render_section_title("Execution Strategy")
    kpi_row({
        "Selected Engine":    ", ".join(data.get("selected_solver", [])),
        "Execution Mode":     data.get("execution_mode", "—").upper(),
        "Fallback Handler":   data.get("fallback_solver") or "None",
        "Runtime Directive":  data.get("runtime_hint", "—").upper(),
    })

    st.markdown("<br>", unsafe_allow_html=True)
    render_section_title("Algorithmic Reasoning")
    st.markdown(f"> *{data.get('reasoning', '—')}*")

    limits = cfg.get("solver_selection", {}).get("limits", {})
    if limits:
        render_section_title("Active Decision Threshold limits")
        render_caption("Operational logic bounds extracted dynamically from global config.")
        st.json(limits)
