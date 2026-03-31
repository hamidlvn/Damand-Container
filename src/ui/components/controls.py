"""
ui/components/controls.py
Run-stage and run-pipeline button helpers.
"""
import streamlit as st
from typing import Callable, Optional


def run_stage_button(
    stage_key: str,
    label: str = "▶  Run Stage",
    fn: Optional[Callable] = None,
    config: Optional[dict] = None,
) -> None:
    """
    Renders a run button for a single stage.
    On click it calls fn(config=config) and clears the data cache.
    """
    if st.button(label, key=f"run_{stage_key}"):
        if fn is None:
            st.warning("Stage function not wired yet.")
            return
        with st.spinner(f"Running {stage_key}…"):
            try:
                fn(config=config)
                st.cache_data.clear()
                st.success("Stage completed successfully.")
            except Exception as e:
                st.error(f"Stage failed: {e}")


def run_pipeline_button(
    mode: str = "full",
    start_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
    config: Optional[dict] = None,
) -> None:
    """Renders a full-pipeline run button."""
    from src.orchestrator.runner import execute_pipeline
    from src.ui.utils import PROJECT_ROOT

    label = f"▶  Run Pipeline ({mode})"
    if st.button(label, key=f"run_pipeline_{mode}"):
        with st.spinner("Running pipeline…"):
            try:
                summary = execute_pipeline(
                    mode=mode,
                    start_stage=start_stage,
                    only_stage=only_stage,
                    config=config,
                    cwd=PROJECT_ROOT,
                )
                st.cache_data.clear()
                status = summary.get("status", "unknown")
                if status == "success":
                    st.success(f"Pipeline finished in {summary.get('duration_seconds', '?')}s")
                elif status == "dry_run":
                    st.info("Dry-run complete — no stages executed.")
                else:
                    errors = summary.get("errors", [])
                    st.error(f"Pipeline failed: {'; '.join(errors[:2])}")
            except Exception as e:
                st.error(f"Pipeline runner error: {e}")
