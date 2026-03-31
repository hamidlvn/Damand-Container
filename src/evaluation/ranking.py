"""
ranking.py
==========
Deterministic, configurable ranking of solver KPI records.

Default priority order (lexicographic – earlier = more important):
  1. status_rank        (lower is better: optimal < feasible < infeasible < failed)
  2. unmet_demand_teu   (lower is better – service quality)
  3. total_cost         (lower is better – economic efficiency)
  4. solve_time_seconds (lower is better – operational speed)

All rules are transparent and documented here so they can be replicated in a
methods section of a research paper.
"""

from typing import Any, Dict, List, Optional, Tuple


DEFAULT_RANKING_RULES: List[Tuple[str, bool]] = [
    ("status_rank",        False),   # ascending (0 = optimal is best)
    ("unmet_demand_teu",   False),   # ascending
    ("total_cost",         False),   # ascending
    ("solve_time_seconds", False),   # ascending
]


def rank_solvers(
    kpi_records: List[Dict[str, Any]],
    rules: List[Tuple[str, bool]] = None,
) -> Dict[str, Any]:
    """
    Ranks solver KPI records deterministically and returns a structured ranking output.

    Parameters
    ----------
    kpi_records : list of KPI dicts (from solver_eval.result_to_kpi_record)
    rules       : list of (field_name, descending) tuples defining sort order.
                  Defaults to DEFAULT_RANKING_RULES.

    Returns
    -------
    {
        "ranked_solvers"  : [...],   # sorted KPI records, best first
        "best_solver"     : str,     # name of the top-ranked solver
        "ranking_explanation": str,  # human-readable rationale
        "trade_off_notes" : [...],   # any notable trade-offs between top solvers
    }
    """
    if not kpi_records:
        return {
            "ranked_solvers":       [],
            "best_solver":          None,
            "ranking_explanation":  "No solver results available to rank.",
            "trade_off_notes":      [],
        }

    if rules is None:
        rules = DEFAULT_RANKING_RULES

    # Build sort key tuple for each record
    def sort_key(rec: Dict[str, Any]) -> tuple:
        return tuple(
            (-rec.get(field, 0) if descending else rec.get(field, float("inf")))
            for field, descending in rules
        )

    ranked = sorted(kpi_records, key=sort_key)

    # ── label each rank position ──────────────────────────────────────────
    for i, rec in enumerate(ranked):
        rec["rank"] = i + 1

    best = ranked[0]

    # ── build human-readable explanation ─────────────────────────────────
    rule_labels = {
        "status_rank":        "feasibility status",
        "unmet_demand_teu":   "unmet demand (TEU)",
        "total_cost":         "total transport cost",
        "solve_time_seconds": "solve time",
    }
    applied_labels = [rule_labels.get(r, r) for r, _ in rules]
    explanation = (
        f"'{best['solver_name']}' ranked first based on the following priority rules "
        f"(applied lexicographically): {', '.join(applied_labels)}. "
        f"It achieved status='{best['status']}', "
        f"unmet_demand={best['unmet_demand_teu']} TEU, "
        f"cost=${best['total_cost']:,.2f}, "
        f"service_level={best['service_level_pct']}%."
    )

    # ── trade-off notes (compare top-2 if benchmark mode) ────────────────
    trade_off_notes: List[str] = []
    if len(ranked) >= 2:
        second = ranked[1]
        # Cost trade-off
        if second["total_cost"] < best["total_cost"]:
            diff = best["total_cost"] - second["total_cost"]
            trade_off_notes.append(
                f"'{second['solver_name']}' has a lower cost by ${diff:,.2f} "
                f"but ranked lower due to higher unmet demand or worse status."
            )
        # Service trade-off
        if second["service_level"] > best["service_level"]:
            diff = (second["service_level"] - best["service_level"]) * 100
            trade_off_notes.append(
                f"'{second['solver_name']}' achieves {diff:.2f}% higher service level "
                f"but at a higher cost."
            )
        # Speed trade-off
        if second["solve_time_seconds"] < best["solve_time_seconds"]:
            trade_off_notes.append(
                f"'{second['solver_name']}' solved {best['solve_time_seconds'] - second['solve_time_seconds']:.4f}s "
                f"faster than '{best['solver_name']}'."
            )

    return {
        "ranked_solvers":      ranked,
        "best_solver":         best["solver_name"],
        "ranking_explanation": explanation,
        "trade_off_notes":     trade_off_notes,
        "ranking_rules_applied": [
            {"field": f, "direction": "desc" if d else "asc"} for f, d in rules
        ],
    }
