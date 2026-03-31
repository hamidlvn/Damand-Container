"""
forecasting_eval.py
====================
Reads the Stage 3 model_evaluations.parquet artifact and produces a structured
forecast evaluation: per-series metrics, cross-model comparison, and best-model
identification — organized by (port, container_type, target_variable).
"""

import pandas as pd
from typing import Any, Dict, List


# ── internal schema ─────────────────────────────────────────────────────────

def _series_summary(group: pd.DataFrame, group_key: tuple) -> Dict[str, Any]:
    """
    Build a single record summarising all models evaluated on one
    (port, container_type, target_variable) series.
    """
    port, ctype, target = group_key
    models: List[Dict[str, Any]] = []
    best_row = group[group["is_best_model"] == True]  # noqa: E712

    for _, row in group.iterrows():
        models.append({
            "model_name":    row["model_name"],
            "mae":           round(float(row["mae"]),   4),
            "rmse":          round(float(row["rmse"]),  4),
            "smape":         round(float(row["smape"]), 4),
            "is_best_model": bool(row["is_best_model"]),
        })

    best_model = best_row.iloc[0]["model_name"] if not best_row.empty else "Naive"
    best_smape = float(best_row.iloc[0]["smape"]) if not best_row.empty else None

    return {
        "port":            port,
        "container_type":  ctype,
        "target_variable": target,
        "models_evaluated": models,
        "best_model":      best_model,
        "best_smape":      round(best_smape, 4) if best_smape is not None else None,
    }


def evaluate_forecasts(eval_parquet_path: str) -> Dict[str, Any]:
    """
    Reads model_evaluations.parquet and returns a structured evaluation dict.
    Structure:
      {
        "series": [...],               # per (port, ctype, target) records
        "aggregate_by_target": {...},  # mean KPIs averaged over ports/types
        "overall_best_models": {...},  # most-frequent best model per target
      }
    """
    try:
        df = pd.read_parquet(eval_parquet_path)
    except FileNotFoundError:
        return {"error": f"Forecast evaluation artifact not found: {eval_parquet_path}"}

    required_cols = {"port", "container_type", "target_variable", "model_name",
                     "mae", "rmse", "smape", "is_best_model"}
    missing = required_cols - set(df.columns)
    if missing:
        return {"error": f"Missing columns in evaluation artifact: {missing}"}

    series_records: List[Dict[str, Any]] = []
    grouped = df.groupby(["port", "container_type", "target_variable"])
    for key, grp in grouped:
        series_records.append(_series_summary(grp, key))

    # ── aggregate by target variable ──────────────────────────────────────
    agg_by_target: Dict[str, Any] = {}
    for target in df["target_variable"].unique():
        best_rows = df[(df["target_variable"] == target) & (df["is_best_model"] == True)]  # noqa
        if best_rows.empty:
            continue
        agg_by_target[target] = {
            "mean_mae":   round(best_rows["mae"].mean(),   4),
            "mean_rmse":  round(best_rows["rmse"].mean(),  4),
            "mean_smape": round(best_rows["smape"].mean(), 4),
            "series_count": int(len(best_rows)),
        }

    # ── most frequent best model per target ──────────────────────────────
    best_models: Dict[str, str] = {}
    for target in df["target_variable"].unique():
        best_rows = df[(df["target_variable"] == target) & (df["is_best_model"] == True)]  # noqa
        if not best_rows.empty:
            best_models[target] = best_rows["model_name"].mode().iloc[0]

    return {
        "series":              series_records,
        "aggregate_by_target": agg_by_target,
        "overall_best_models": best_models,
    }
