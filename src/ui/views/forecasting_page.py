import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_parquet
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.charts import line_chart, bar_chart
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.forecasting.service import generate_forecasts


def render():
    render_page_header(
        title_en="Stage 3 — Forecasting",
        title_fa="مرحله ۳ — پیش‌بینی سری‌های زمانی",
        desc_en="This stage leverages statistical (Theta, HW) and machine learning (RF) models to predict future demand, supply, and net balances. It generates the mathematical baseline for optimization.",
        desc_fa="در این مرحله، تقاضا، عرضه و عدم تعادل آینده با استفاده از مدل‌های آماری و یادگیری ماشین پیش‌بینی می‌شود. این خروجی، پایه و اساس تصمیم‌گیری و بهینه‌سازی مراحل بعدی خواهد بود."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("forecasting", fn=generate_forecasts, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_fc"):
            st.cache_data.clear()

    if dependency_warning("forecasting"):
        return

    artifact_panel(["forecast_results.parquet", "model_evaluations.parquet"])

    df_fc  = read_parquet("forecast_results.parquet")
    df_ev  = read_parquet("model_evaluations.parquet")

    # ── Model Evaluation table ─────────────────────────────────────────────
    if df_ev is not None:
        render_section_title("Algorithm Performance & Model Selection")
        best_counts = (
            df_ev[df_ev["is_best_model"] == True]  # noqa
            .groupby("model_name")
            .size()
            .reset_index(name="times_selected_as_best")
        )
        kpi_row({
            "Series Evaluated": f"{df_ev[['port','container_type','target_variable']].drop_duplicates().__len__():,}",
            "Models Configured": str(df_ev["model_name"].nunique()),
        })
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_ev, col_best = st.columns(2)
        with col_ev:
            render_caption("Error metrics tracking tracking (Top performing models per node).")
            show_df(
                df_ev[df_ev["is_best_model"] == True][["port","container_type","target_variable","model_name","mae","rmse","smape"]]  # noqa
                .round(3), max_rows=80
            )
        with col_best:
            render_caption("Frequency distribution of winning forecasting algorithms.")
            bar_chart(best_counts, x="model_name", y="times_selected_as_best",
                      title="Selection Frequency")

    # ── Forecast preview ───────────────────────────────────────────────────
    if df_fc is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_title("Forecasting Output Explorer")
        
        if "port" in df_fc.columns:
            ports   = sorted(df_fc["port"].unique())
            targets = sorted(df_fc["forecast_type"].unique()) if "forecast_type" in df_fc.columns else []
            
            col_sel1, col_sel2 = st.columns(2)
            sel_port   = col_sel1.selectbox("Filter Target Port:",   ports,   key="fc_port_sel")
            sel_target = col_sel2.selectbox("Filter Target Variable:", targets, key="fc_tgt_sel")
            
            sub = df_fc[(df_fc["port"] == sel_port) & (df_fc["forecast_type"] == sel_target)]
            line_chart(sub, x="target_period", y=["point_estimate"],
                       title=f"Projected {sel_target.title()} — {sel_port}")
                       
            render_caption("Structured point estimates output ready for Constraints scaling.")
            show_df(sub, max_rows=50)
    else:
        st.info("Wait... Run the Forecasting stage above to synthesize data predictions.")
