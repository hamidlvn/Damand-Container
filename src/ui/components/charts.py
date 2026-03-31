"""
ui/components/charts.py  –  Lightweight chart helpers.
"""
import pandas as pd
import streamlit as st
from typing import Optional


def line_chart(
    df: Optional[pd.DataFrame],
    x: str,
    y: list,
    title: str = "",
    height: int = 300,
) -> None:
    if df is None or df.empty:
        st.info("No data to chart.")
        return
    if title:
        st.caption(title)

    plot_df = df[[x] + [c for c in y if c in df.columns]].copy()
    plot_df[x] = pd.to_datetime(plot_df[x], errors="coerce")
    plot_df = plot_df.set_index(x).sort_index()
    st.line_chart(plot_df, height=height, use_container_width=True)


def bar_chart(
    df: Optional[pd.DataFrame],
    x: str,
    y: str,
    title: str = "",
    height: int = 300,
) -> None:
    if df is None or df.empty:
        st.info("No data to chart.")
        return
    if title:
        st.caption(title)
    plot_df = df[[x, y]].set_index(x)
    st.bar_chart(plot_df, height=height, use_container_width=True)
