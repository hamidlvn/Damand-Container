"""
ui/utils.py – shared helpers for loading artifacts and config.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RESULTS_DIR   = PROJECT_ROOT / "results"
CONFIG_PATH   = PROJECT_ROOT / "configs" / "pipeline.yaml"


@st.cache_data(ttl=30)
def load_config() -> Dict[str, Any]:
    from src.utils.config import load_config as _load
    return _load(str(CONFIG_PATH))


def artifact_path(filename: str) -> Path:
    return PROCESSED_DIR / filename


def artifact_exists(filename: str) -> bool:
    return artifact_path(filename).exists()


@st.cache_data(ttl=10)
def read_parquet(filename: str) -> Optional[pd.DataFrame]:
    p = artifact_path(filename)
    if not p.exists():
        return None
    try:
        return pd.read_parquet(p)
    except Exception as e:
        st.warning(f"Could not read {filename}: {e}")
        return None


@st.cache_data(ttl=10)
def read_json(filename: str) -> Optional[Dict[str, Any]]:
    p = artifact_path(filename)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Could not read {filename}: {e}")
        return None


@st.cache_data(ttl=10)
def read_results_json(filename: str) -> Optional[Dict[str, Any]]:
    p = RESULTS_DIR / filename
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None


def read_markdown(filename: str) -> Optional[str]:
    p = artifact_path(filename)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def fmt_teu(v: float) -> str:
    return f"{v:,.1f} TEU"


def fmt_cost(v: float) -> str:
    return f"${v:,.0f}"


def fmt_pct(v: float) -> str:
    return f"{v:.1%}"
