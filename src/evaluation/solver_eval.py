"""
solver_eval.py
==============
Reads one or more SolverResult JSON artifacts and normalises them into a
side-by-side comparison table with clear, machine-readable KPI records.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.schemas.core import SolverResult


# ── status ordering used by ranking.py ──────────────────────────────────────
STATUS_RANK = {
    "optimal":                  0,
    "feasible":                 1,
    "feasible_with_violations": 2,
    "infeasible":               3,
    "failed":                   4,
}


def load_solver_result(path: str) -> Optional[SolverResult]:
    """Safe loader – returns None if missing or malformed."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, "r") as f:
            return SolverResult.model_validate_json(f.read())
    except Exception:
        return None


def result_to_kpi_record(r: SolverResult) -> Dict[str, Any]:
    """Flatten a SolverResult into a flat, display-ready dict."""
    budget_ok = len(r.diagnostics.get("budget_violations", [])) == 0
    return {
        "solver_name":           r.solver_name,
        "status":                r.status,
        "status_rank":           STATUS_RANK.get(r.status, 99),
        "objective_value":       r.objective_value,
        "total_cost":            r.total_cost,
        "service_level":         r.service_level,
        "service_level_pct":     round(r.service_level * 100, 2),
        "unmet_demand_teu":      r.unmet_demand_teu,
        "surplus_remaining_teu": r.surplus_remaining_teu,
        "solve_time_seconds":    r.solve_time_seconds,
        "total_moves":           len(r.decisions),
        "budget_adherence":      budget_ok,
        "diagnostics":           r.diagnostics,
    }


def evaluate_solvers(result_paths: List[str]) -> Dict[str, Any]:
    """
    Loads all available SolverResult files, converts to KPI records, and
    returns a structured evaluation dict containing:
      - solver_kpis   : per-solver flat records
      - available_solvers : names of successfully loaded solvers
      - failed_solvers    : names that could not be loaded
    """
    kpis: List[Dict[str, Any]] = []
    failed: List[str] = []

    for path in result_paths:
        result = load_solver_result(path)
        if result is None:
            failed.append(path)
            continue
        kpis.append(result_to_kpi_record(result))

    return {
        "solver_kpis":       kpis,
        "available_solvers": [k["solver_name"] for k in kpis],
        "failed_solvers":    failed,
    }
