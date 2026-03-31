import streamlit as st
from src.ui.utils import artifact_exists, load_config, PROCESSED_DIR, RESULTS_DIR
from src.ui.components.artifact_status import status_badge
from src.orchestrator.pipeline import STAGES
from src.ui.components.text import render_page_header, render_section_title


def render():
    render_page_header(
        title_en="🏠 Empty Container DSS — Prototype",
        title_fa="مدیریت و بهینه‌سازی کانتینرهای خالی — خانه",
        desc_en="A modular, multi-modal Decision Support System for empty container repositioning. Built for complex analytical logistics and research-grade optimization.",
        desc_fa="یک سیستم پشتیبان تصمیم‌گیری انعطاف‌پذیر و پژوهش‌محور برای مدیریت، جابجایی و بهینه‌سازی توزیع کانتینرهای خالی در شبکه‌های حمل‌و‌نقل."
    )

    # ── Config snapshot ────────────────────────────────────────────────────
    cfg = load_config()
    st.subheader("📋 Active Configuration")
    col1, col2, col3 = st.columns(3)
    col1.metric("Random Seed", cfg.get("reproducibility", {}).get("random_seed", 42))
    col2.metric("Forecast Horizon", f"{cfg.get('forecasting', {}).get('horizon_periods', '?')} periods")
    col3.metric("Service Level Target",
                f"{cfg.get('constraints', {}).get('global_service_level_target', 0.9):.0%}")

    st.divider()

    # ── Stage pipeline status table ────────────────────────────────────────
    st.subheader("🔁 Pipeline Stage Status")
    rows = []
    for spec in STAGES:
        all_ok = all(artifact_exists(a.replace("data/processed/", "")) for a in spec.artifacts) if spec.artifacts else None
        if all_ok is True:
            indicator = "✅ Ready"
        elif all_ok is False:
            indicator = "❌ Pending"
        else:
            indicator = "⏳ No artifacts defined"
        rows.append({
            "Stage": spec.display_name,
            "Dependencies": ", ".join(spec.depends_on) or "—",
            "Status": indicator,
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()

    # ── Run summary ────────────────────────────────────────────────────────
    st.subheader("📊 Last Run Summary")
    summary_path = RESULTS_DIR / "run_summary.json"
    if summary_path.exists():
        import json
        s = json.loads(summary_path.read_text())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Run ID",     s.get("run_id", "—"))
        c2.metric("Status",     s.get("status", "—").upper())
        c3.metric("Duration",   f"{s.get('duration_seconds', 0):.1f}s")
        c4.metric("Stages Run", len(s.get("stages_executed", [])))
        if s.get("errors"):
            st.error("Errors: " + "; ".join(s["errors"][:3]))
    else:
        st.info("No run summary found. Run the full pipeline to get started.")
