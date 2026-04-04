import streamlit as st
from src.ui.utils import load_config, read_parquet
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.ingestion.loader import ingest_dataset


def render():
    render_page_header(
        title_en="Stage 1 — Data Loading",
        title_fa="مرحله ۱ — دریافت و بارگذاری داده‌ها",
        desc_en="This stage loads raw historical port data and validates physical boundaries using strict Pydantic schemas. It establishes a robust foundation for all subsequent modeling.",
        desc_fa="در این مرحله، داده‌های خام تاریخچه بنادر دریافت شده و از لحاظ صحت مقادیر ფیزیکی تحت بررسی دقیق اسکیماهای Pydantic قرار می‌گیرد. این ساختار پایه تمام مراحل تحلیلی بعدی است."
    )

    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        cfg = load_config()
        run_stage_button("ingestion", fn=ingest_dataset, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_ingestion"):
            st.cache_data.clear()

    artifact_panel(["cleaned_history.parquet"], "Ingestion Artifacts")

    df = read_parquet("cleaned_history.parquet")
    if df is not None:
        render_section_title("Dataset Summary")
        kpi_row({
            "Cleaned Rows": f"{len(df):,}",
            "Unique Ports": df["port"].nunique() if "port" in df.columns else "—",
            "Container Types": df["container_type"].nunique() if "container_type" in df.columns else "—",
            "Data Horizon": f"{df['date'].min()} → {df['date'].max()}" if "date" in df.columns else "—",
        })
        
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_title("Preview")
        render_caption("Top 100 entries of the fully validated historical database.")
        show_df(df, max_rows=100)
    else:
        st.info("Wait... Run the Ingestion stage above to compile the dataset.")
