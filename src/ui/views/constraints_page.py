import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_json
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.constraints.service import generate_constraints


def render():
    render_page_header(
        title_en="Stage 4 — Constraints Modeling",
        title_fa="مرحله ۴ — مدل‌سازی محدودیت‌های تجاری",
        desc_en="This stage parses strategic business rules encompassing inventory bounds, target service levels, and financial budgets. It translates these business priorities into strict mathematical penalties for the solvers.",
        desc_fa="در این مرحله، قوانین راهبردی کسب‌وکار مانند کران‌های موجودی، سطح سرویس‌دهی و بودجه بررسی می‌شود. این اولویت‌ها به شکل جریمه‌های دقیق ریاضی برای استفاده در الگوریتم‌های بهینه‌سازی فرموله می‌شوند."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("constraints", fn=generate_constraints, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_con"):
            st.cache_data.clear()

    if dependency_warning("constraints"):
        return

    artifact_panel(["business_constraints.json"])

    data = read_json("business_constraints.json")
    if data is None:
        st.info("Wait... Run the Constraints stage above to compile business rules.")
        return

    # Global KPIs
    render_section_title("Global Operations Policy")
    budget = data.get("budget", {})
    kpi_row({
        "Service Level Target": f"{data.get('global_service_level_target', 0):.0%}",
        "Budget Limit":         f"${budget.get('limit_value', 0):,.0f}",
        "Budget Type":          "Hard Constraint" if budget.get("is_hard_limit") else "Soft Constraint",
        "Shortage Penalty":     f"${data.get('shortage_penalty', 0):.0f}/TEU",
        "Surplus Penalty":      f"${data.get('surplus_penalty', 0):.0f}/TEU",
    })

    st.markdown("<br>", unsafe_allow_html=True)
    render_section_title("Port-Level Safety Stock Constraints")
    pcs = data.get("port_constraints", [])
    if pcs:
        df_pc = pd.DataFrame(pcs)
        render_caption("Localized inventory bounds enforcing physical storage limits.")
        show_df(df_pc)
    else:
        st.info("No localized per-port constraints defined.")

    render_section_title("Financial Budget Parameters")
    render_caption("Raw JSON parameters governing the objective cost functions.")
    st.json(budget)
