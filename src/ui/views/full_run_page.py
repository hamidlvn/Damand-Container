import streamlit as st
import pandas as pd
from src.ui.utils import load_config, read_results_json, RESULTS_DIR, PROJECT_ROOT
from src.ui.components.controls import run_pipeline_button
from src.orchestrator.pipeline import STAGES, STAGE_ORDER


def render():
    st.header("🚀 Full Pipeline Run")
    st.caption("Execute the entire 10-stage pipeline end-to-end, or run partial sequences.")

    cfg = load_config()

    # ── Run mode controls ──────────────────────────────────────────────────
    st.subheader("Execution Settings")
    col1, col2 = st.columns(2)

    with col1:
        mode = st.selectbox(
            "Run Mode",
            ["full", "from_stage", "single_stage", "dry_run"],
            key="full_run_mode",
        )

    with col2:
        stage_needed = mode in ("from_stage", "single_stage")
        sel_stage = st.selectbox(
            "Stage" + (" *" if stage_needed else " (N/A for full/dry)"),
            STAGE_ORDER,
            disabled=not stage_needed,
            key="full_run_stage_sel",
        )

    seed = cfg.get("reproducibility", {}).get("random_seed", 42)
    st.caption(f"Random seed: **{seed}** (set in `configs/pipeline.yaml`)")

    # ── Run button ─────────────────────────────────────────────────────────
    start_stage = sel_stage if mode == "from_stage"   else None
    only_stage  = sel_stage if mode == "single_stage" else None
    dry_run     = (mode == "dry_run")

    from src.orchestrator.runner import execute_pipeline

    if st.button("▶  Execute", type="primary", key="full_run_exec_btn"):
        with st.spinner("Running pipeline…"):
            try:
                summary = execute_pipeline(
                    mode        = mode,
                    start_stage = start_stage,
                    only_stage  = only_stage,
                    dry_run     = dry_run,
                    config      = cfg,
                    cwd         = PROJECT_ROOT,
                )
                st.cache_data.clear()
                status = summary.get("status", "unknown")
                if status in ("success", "dry_run"):
                    st.success(f"Done in {summary.get('duration_seconds', 0):.1f}s — status: **{status}**")
                else:
                    st.error(f"Pipeline failed: {'; '.join(summary.get('errors', [])[:3])}")
                st.session_state["last_summary"] = summary
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    st.divider()

    # ── Stage plan preview ─────────────────────────────────────────────────
    st.subheader("Stage Execution Plan")
    from src.orchestrator.dependencies import resolve_stage_sequence
    try:
        planned = resolve_stage_sequence(start_stage=start_stage, only_stage=only_stage)
        skipped = [s for s in STAGE_ORDER if s not in planned]
        rows = []
        for spec in STAGES:
            if spec.key in planned:
                rows.append({"Stage": spec.display_name, "Planned": "✅ Will run", "Dependencies": ", ".join(spec.depends_on) or "—"})
            else:
                rows.append({"Stage": spec.display_name, "Planned": "⏭️ Skipped", "Dependencies": ", ".join(spec.depends_on) or "—"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    except Exception:
        pass

    # ── Last run summary ───────────────────────────────────────────────────
    st.divider()
    st.subheader("Last Run Summary")
    summary = read_results_json("run_summary.json")
    if summary is None and "last_summary" in st.session_state:
        summary = st.session_state["last_summary"]

    if summary:
        c1, c2, c3 = st.columns(3)
        c1.metric("Run ID",   summary.get("run_id", "—"))
        c2.metric("Status",   summary.get("status", "—").upper())
        c3.metric("Duration", f"{summary.get('duration_seconds', 0):.1f}s")

        stage_results = summary.get("stages_executed", [])
        if stage_results:
            df_sr = pd.DataFrame(stage_results)
            st.dataframe(df_sr, use_container_width=True, hide_index=True)

        errors = summary.get("errors", [])
        if errors:
            st.error("Errors encountered:")
            for e in errors:
                st.caption(e)
    else:
        st.info("No run summary found yet.")
