"""
ui/components/tables.py  –  Dataframe display helpers.
"""
import pandas as pd
import streamlit as st
from typing import Optional


def show_df(
    df: Optional[pd.DataFrame],
    max_rows: int = 200,
    caption: str = "",
) -> None:
    if df is None:
        st.info("No data available yet. Run the stage first.")
        return
    if caption:
        st.caption(caption)
    st.dataframe(df.head(max_rows), use_container_width=True)


def kpi_row(metrics: dict) -> None:
    """Renders a horizontal row of KPI metric cards."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label, value)


def json_table(data: dict, key_col: str = "Key", val_col: str = "Value") -> None:
    """Flattens a simple dict into a two-column DataFrame."""
    rows = [(k, str(v)) for k, v in data.items() if not isinstance(v, (dict, list))]
    df = pd.DataFrame(rows, columns=[key_col, val_col])
    show_df(df)
