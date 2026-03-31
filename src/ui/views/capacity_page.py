import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_json
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.capacity.service import generate_capacity


def render():
    render_page_header(
        title_en="Stage 5 — Capacity Modeling",
        title_fa="مرحله ۵ — مدل‌سازی شبکه‌های ترابری و ظرفیت",
        desc_en="This stage synthesizes the dynamic multi-modal physical transport network. It establishes discrete voyage graphs specifying limits, timelines, and costs for Sea, Rail, and Road constraints.",
        desc_fa="در این مرحله، گراف پویای شبکه‌های ترابری چندگانه (دریا، ریلی و جاده‌ای) ایجاد می‌شود. برای هر مسیر محدودیت‌های ظرفیتی، زمانی و هزینه‌ای به طور دقیق مشخص می‌گردد."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("capacity", fn=generate_capacity, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_cap"):
            st.cache_data.clear()

    if dependency_warning("capacity"):
        return

    artifact_panel(["transport_capacity.json"])

    data = read_json("transport_capacity.json")
    if data is None:
        st.info("Wait... Run the Capacity Modeling stage above to build the physical network.")
        return

    legs = data.get("voyage_legs", [])
    if not legs:
        st.warning("No voyage legs found in artifact.")
        return

    df = pd.DataFrame(legs)

    render_section_title("Operational Network Summary")
    kpi_row({
        "Transport Arcs Generated": f"{len(df):,}",
        "Operating Nodes":       str(df["origin_port"].nunique()) if "origin_port" in df.columns else "—",
        "Capacity Range / Leg": f"{df['capacity_teu'].min():.0f}–{df['capacity_teu'].max():.0f} TEU" if "capacity_teu" in df.columns else "—",
        "Transit Range":        f"{df['transit_time_periods'].min()}–{df['transit_time_periods'].max()} Periods" if "transit_time_periods" in df.columns else "—",
        "Avg Movement Cost":         f"${df['cost_per_teu'].mean():.0f}/TEU" if "cost_per_teu" in df.columns else "—",
    })

    st.markdown("<br>", unsafe_allow_html=True)
    render_section_title("Generated Voyage Logs")
    render_caption("Discrete synthetic route allocations bounding physical shipping capacities across all multi-modal channels.")
    show_df(df, max_rows=100)
