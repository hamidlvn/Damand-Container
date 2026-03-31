import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_json
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.problem.service import generate_problem


def render():
    render_page_header(
        title_en="Stage 6 — Problem Builder",
        title_fa="مرحله ۶ — پیکربندی ساختار ریاضی مسئله",
        desc_en="This orchestrator merges multi-modal transport capacities, time-series forecasted demands, and operating parameters into a single, unified mathematical structured matrix.",
        desc_fa="در این مرحله، تمامی پیش‌بینی‌های سری زمانی، محدودیت‌های عملیاتی و ماتریس‌های ترابری در قالب یک بسته منسجم ریاضیاتی به نام StructuredProblem مونتاژ می‌شود."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("problem_builder", fn=generate_problem, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_prob"):
            st.cache_data.clear()

    if dependency_warning("problem_builder"):
        return

    artifact_panel(["structured_problem.json"])

    data = read_json("structured_problem.json")
    if data is None:
        st.info("Wait... Run the Problem Builder stage above to integrate the final matrix.")
        return

    ports   = data.get("ports", [])
    periods = data.get("time_periods", [])
    ctypes  = data.get("container_types", [])
    arcs    = data.get("arcs", [])

    render_section_title("Operational Topology Summary")
    kpi_row({
        "Problem ID":     str(data.get("problem_id", "—")),
        "Ports":          str(len(ports)),
        "Time Periods":   str(len(periods)),
        "Container Types":str(len(ctypes)),
        "Transport Arcs": str(len(arcs)),
    })

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        render_section_title("Monitored Ports")
        render_caption("Indexed port identifiers mapped dynamically.")
        st.write(ports)
    with col2:
        render_section_title("Chronological Periods")
        render_caption("Linear projection sequence for matrix operations.")
        st.write(periods[:10])

    st.markdown("<br>", unsafe_allow_html=True)
    render_section_title("Transport Arcs Indexed Matrix")
    if arcs:
        render_caption("Final solver-ready array tracking mode, capabilities, schedule, and cost paths.")
        show_df(pd.DataFrame(arcs[:50]))
    else:
        st.info("No arcs generated.")

    st.markdown("<br>", unsafe_allow_html=True)
    render_section_title("Structured Demand Matrix (Sample)")
    dem = data.get("demand_matrix", {})
    if dem:
        rows = [(p, t, v) for p, td in dem.items() for t, v in td.items()]
        render_caption("Unrolled numerical matrix feeding directly into objective solvers.")
        show_df(pd.DataFrame(rows, columns=["port", "t_idx", "demand_teu"]).head(50))
