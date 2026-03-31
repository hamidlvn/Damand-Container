import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_json
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.charts import bar_chart
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.evaluation.service import evaluate_pipeline


def render():
    render_page_header(
        title_en="Stage 9 — Evaluation",
        title_fa="مرحله ۹ — ارزیابی مدل‌ها و انتخاب بهترین استراتژی",
        desc_en="This module comparatively evaluates forecasting errors alongside solver multi-objective KPIs. It automatically ranks operational strategies based on balanced trade-offs between cost, service level, and feasibility.",
        desc_fa="این ماژول، دقت مدل‌های پیش‌بینی را در کنار نتایج موتورهای بهینه‌سازی ارزیابی می‌کند. سپس بر اساس تعادل بین هزینه، سطح سرویس و امکان‌پذیری فیزیکی، بهترین استراتژی عملیاتی را انتخاب و رتبه‌بندی می‌کند."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("evaluation", fn=evaluate_pipeline, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_ev"):
            st.cache_data.clear()

    if dependency_warning("evaluation"):
        return

    artifact_panel(["forecast_evaluation.json", "solver_evaluation.json", "evaluation_summary.json"])

    summary = read_json("evaluation_summary.json")
    fc_eval = read_json("forecast_evaluation.json")

    if not summary and not fc_eval:
        st.info("Wait... Run the Evaluation stage above to compute comparative performance metrics.")
        return

    # ── Solver ranking ─────────────────────────────────────────────────────
    if summary:
        render_section_title("🏆 Operational Strategy Ranking")
        kpi_row({"Selected Optimal Solver": str(summary.get("best_solver", "—"))})
        
        st.markdown(f"> *{summary.get('ranking_explanation', '')}*")

        ranked = summary.get("ranked_solvers", [])
        if ranked:
            render_caption("Execution metrics comparison across parallel solver runs.")
            df_rank = pd.DataFrame(ranked)
            cols_show = ["rank", "solver_name", "status", "service_level_pct",
                         "unmet_demand_teu", "total_cost", "solve_time_seconds"]
            show_df(df_rank[[c for c in cols_show if c in df_rank.columns]])

        notes = summary.get("trade_off_notes", [])
        if notes:
            st.markdown("<br>", unsafe_allow_html=True)
            render_section_title("Trade-off Analysis Notes")
            for n in notes:
                st.info(n)

    # ── Forecast summary ───────────────────────────────────────────────────
    if fc_eval and not fc_eval.get("error"):
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_title("📊 Forecasting Accuracy Overview")
        agg = fc_eval.get("aggregate_by_target", {})
        if agg:
            render_caption("Aggregated MAPE and RMSE error brackets per core feature target.")
            rows = [{"target": t, **v} for t, v in agg.items()]
            show_df(pd.DataFrame(rows))

        best_models = fc_eval.get("overall_best_models", {})
        if best_models:
            render_caption("Dominant algorithms auto-selected during competition.")
            st.json(best_models)
