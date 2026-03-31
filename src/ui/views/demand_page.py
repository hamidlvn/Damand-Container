import streamlit as st
from src.ui.utils import load_config, read_parquet
from src.ui.components.artifact_status import artifact_panel, dependency_warning
from src.ui.components.controls import run_stage_button
from src.ui.components.tables import show_df, kpi_row
from src.ui.components.charts import line_chart
from src.ui.components.text import render_page_header, render_section_title, render_caption
from src.demand.service import process_demand_layer


def render():
    render_page_header(
        title_en="Stage 2 — Demand Management",
        title_fa="مرحله ۲ — مدیریت تقاضا و عدم تعادل",
        desc_en="This stage parses historical container movements to derive explicit demand and supply signals. It mathematically classifies each port's temporal state into distinct surplus or shortage events.",
        desc_fa="در این مرحله، تحرکات تاریخی کانتینرها تحلیل شده تا سیگنال‌های تقاضا و عرضه استخراج شوند. وضعیت هر بندر در طول زمان به شکل ریاضیاتی به الگوهای مازاد و کمبود دسته‌بندی می‌شود."
    )

    cfg = load_config()
    col_run, col_refresh = st.columns([2, 1])
    with col_run:
        run_stage_button("demand", fn=process_demand_layer, config=cfg)
    with col_refresh:
        if st.button("🔄 Refresh View", key="refresh_demand"):
            st.cache_data.clear()

    if dependency_warning("demand"):
        return

    artifact_panel(["historical_signals.parquet", "historical_net_balance.parquet"])

    df_sig = read_parquet("historical_signals.parquet")
    df_bal = read_parquet("historical_net_balance.parquet")

    if df_sig is not None:
        render_section_title("Inferred Supply & Demand Signals")
        kpi_row({
            "Signal Records": f"{len(df_sig):,}",
            "Port Count": df_sig["port"].nunique() if "port" in df_sig.columns else "—",
            "Monitored Periods": df_sig["period"].nunique() if "period" in df_sig.columns else "—",
        })

        if "port" in df_sig.columns:
            ports = sorted(df_sig["port"].unique())
            sel_port = st.selectbox("Select port for temporal view:", ports, key="dem_port_sel")
            sub = df_sig[df_sig["port"] == sel_port].copy()
            line_chart(sub, x="period", y=["inferred_demand", "inferred_supply"],
                       title=f"Historical Baseline — {sel_port}")
                       
        render_caption("Raw output table of inferred signals.")
        show_df(df_sig, max_rows=100)

    if df_bal is not None:
        render_section_title("Calculated Net Balance Matrix")
        shortage_count = int(df_bal["is_shortage"].sum()) if "is_shortage" in df_bal.columns else "—"
        surplus_count  = int(df_bal["is_surplus"].sum())  if "is_surplus"  in df_bal.columns else "—"
        kpi_row({
            "Shortage Events": str(shortage_count), 
            "Surplus Events": str(surplus_count)
        })
        
        render_caption("Absolute categorization of port imbalances across all periods.")
        show_df(df_bal, max_rows=100)
    else:
        st.info("Wait... Run the Demand Management stage above to calculate balances.")
