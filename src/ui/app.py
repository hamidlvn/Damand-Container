"""
src/ui/app.py  –  Empty Container DSS · Streamlit UI
======================================================
Launch:
    streamlit run src/ui/app.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# ── import all view modules from views/ (not pages/) ──────────────────────
from src.ui.views import (
    overview,
    ingestion_page,
    demand_page,
    forecasting_page,
    constraints_page,
    capacity_page,
    problem_page,
    solver_selection_page,
    optimization_page,
    evaluation_page,
    policy_page,
    full_run_page,
)

# ── ordered page registry ──────────────────────────────────────────────────
PAGES = {
    "🏠  Overview":                overview,
    "1 · 📥  Ingestion":           ingestion_page,
    "2 · 📊  Demand Management":   demand_page,
    "3 · 📈  Forecasting":         forecasting_page,
    "4 · ⚖️  Constraints":         constraints_page,
    "5 · 🚢  Capacity":            capacity_page,
    "6 · 🧩  Problem Builder":     problem_page,
    "7 · 🎯  Solver Selection":    solver_selection_page,
    "8 · ⚙️  Optimization":        optimization_page,
    "9 · 📐  Evaluation":          evaluation_page,
    "10 · 📋  Policy Output":      policy_page,
    "─────────────────":           None,           # visual divider
    "🚀  Full Pipeline Run":       full_run_page,
}


def main():
    st.set_page_config(
        page_title="Empty Container DSS",
        page_icon="🚢",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.markdown("""
        <style>
        /* Professional typography and spacing */
        h1, h2, h3 { font-family: 'Inter', 'Segoe UI', sans-serif !important; font-weight: 600 !important; color: #1e293b !important; }
        h1 { font-size: 1.8rem !important; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.5rem; }
        h2 { font-size: 1.4rem !important; }
        h3 { font-size: 1.2rem !important; }
        p, div, span, label { font-family: 'Inter', 'Segoe UI', Tahoma, sans-serif; color: #334155; }
        
        /* Metric Cards */
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; color: #0f172a !important; }
        [data-testid="stMetricLabel"] { font-size: 0.9rem !important; font-weight: 600 !important; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.05em; }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] { background-color: #f1f5f9 !important; border-right: 1px solid #e2e8f0; }
        .stButton>button { border-radius: 6px !important; font-weight: 500 !important; }
        .stButton>button[kind="primary"] { background-color: #f8fafc !important; color: #0369a1 !important; border: 1px solid #bae6fd !important; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        .stButton>button[kind="secondary"] { border: 1px solid #e2e8f0 !important; background-color: white !important; color: #475569 !important; }
        
        /* Dataframes */
        [data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🚢 Container DSS")
        st.caption("Research Prototype · 12-Stage Pipeline")
        st.divider()

        # Build selectable items (filter out dividers)
        selectable = [k for k, v in PAGES.items() if v is not None]

        # Use session state to remember selection
        if "selected_page" not in st.session_state:
            st.session_state["selected_page"] = selectable[0]

        for label in PAGES:
            if PAGES[label] is None:
                # Visual separator — not clickable
                st.markdown("<hr style='margin:4px 0;opacity:0.3'>", unsafe_allow_html=True)
                continue

            is_active = st.session_state["selected_page"] == label
            btn_style = "primary" if is_active else "secondary"

            if st.button(
                label,
                key=f"nav_{label}",
                use_container_width=True,
                type=btn_style,
            ):
                st.session_state["selected_page"] = label

        st.divider()
        if st.button("🔄  Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache cleared.", icon="✅")

        st.caption("Data: Italy 2018–2025")

    # ── Render selected page ───────────────────────────────────────────────
    selected = st.session_state.get("selected_page", selectable[0])
    page_module = PAGES.get(selected)
    if page_module is not None:
        page_module.render()


if __name__ == "__main__":
    main()
