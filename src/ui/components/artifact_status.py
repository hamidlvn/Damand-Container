"""
ui/components/artifact_status.py
Status badges and artifact existence panels.
"""
import streamlit as st
from src.ui.utils import artifact_exists, artifact_path, PROCESSED_DIR, RESULTS_DIR
from pathlib import Path
from typing import List


def status_badge(exists: bool) -> str:
    return "✅" if exists else "❌"


def artifact_row(label: str, filename: str, in_results: bool = False) -> None:
    base = RESULTS_DIR if in_results else PROCESSED_DIR
    p = base / filename
    ok = p.exists()
    col1, col2 = st.columns([4, 1])
    col1.caption(f"`{filename}`")
    col2.markdown(status_badge(ok))


def artifact_panel(artifacts: List[str], title: str = "Stage Artifacts") -> None:
    with st.expander(title, expanded=False):
        any_missing = False
        for fn in artifacts:
            ok = artifact_exists(fn)
            if not ok:
                any_missing = True
            st.markdown(f"{status_badge(ok)}  `{fn}`")
        if any_missing:
            st.warning("Some artifacts are missing. Run the stage to generate them.")
        else:
            st.success("All artifacts present.")


def dependency_warning(stage_key: str) -> bool:
    """
    Checks the stage's expected dependency artifacts.
    Displays a warning and returns True if dependencies are missing.
    """
    from src.orchestrator.pipeline import STAGE_MAP
    spec = STAGE_MAP.get(stage_key)
    if not spec:
        return False

    from src.orchestrator.dependencies import validate_dependencies
    problems = validate_dependencies(stage_key, cwd=PROCESSED_DIR.parent.parent)
    if problems:
        st.error("⛔ **Missing Dependencies**")
        for p in problems:
            st.caption(p)
        return True
    return False
