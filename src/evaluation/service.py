"""
evaluation/service.py
=====================
Stage 9 orchestrator: loads all upstream artifacts, runs forecast and solver
evaluations, applies ranking, and saves three output JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.evaluation.forecasting_eval import evaluate_forecasts
from src.evaluation.solver_eval import evaluate_solvers
from src.evaluation.ranking import rank_solvers

logger = logging.getLogger(__name__)


def evaluate_pipeline(config: Dict[str, Any] = None) -> None:
    """
    Orchestrates Stage 9 evaluation:
      A) Forecast evaluation  → forecast_evaluation.json
      B) Solver evaluation    → solver_evaluation.json
      C) Ranking summary      → evaluation_summary.json
    """
    if config is None:
        config = load_config()

    processed_dir = Path("data/processed")
    ev_cfg = config.get("evaluation", {})

    # ── A) Forecast evaluation ────────────────────────────────────────────
    logger.info("Stage 9 – Forecast Evaluation …")

    fc_cfg = config.get("forecasting", {})
    eval_parquet = processed_dir / fc_cfg.get("output_evaluations_file", "model_evaluations.parquet")

    forecast_eval = evaluate_forecasts(str(eval_parquet))

    fc_out = processed_dir / ev_cfg.get("output_forecast_eval", "forecast_evaluation.json")
    with open(fc_out, "w") as f:
        json.dump(forecast_eval, f, indent=4, default=str)
    logger.info(f"  Forecast evaluation saved → {fc_out}")

    # ── B) Solver evaluation ──────────────────────────────────────────────
    logger.info("Stage 9 – Solver Evaluation …")

    solver_result_paths = [
        str(processed_dir / "solver_result_heuristic.json"),
        str(processed_dir / "solver_result_milp.json"),
    ]
    solver_eval = evaluate_solvers(solver_result_paths)

    sv_out = processed_dir / ev_cfg.get("output_solver_eval", "solver_evaluation.json")
    with open(sv_out, "w") as f:
        json.dump(solver_eval, f, indent=4, default=str)
    logger.info(
        f"  Solver evaluation saved → {sv_out} "
        f"({len(solver_eval['available_solvers'])} solver(s) compared, "
        f"{len(solver_eval['failed_solvers'])} unavailable)"
    )

    # ── C) Ranking & summary ──────────────────────────────────────────────
    logger.info("Stage 9 – Ranking …")

    ranking = rank_solvers(solver_eval["solver_kpis"])

    summary = {
        "best_solver":          ranking["best_solver"],
        "ranking_explanation":  ranking["ranking_explanation"],
        "trade_off_notes":      ranking["trade_off_notes"],
        "ranking_rules_applied": ranking["ranking_rules_applied"],
        "ranked_solvers":       ranking["ranked_solvers"],
        "forecast_summary": {
            "aggregate_by_target": forecast_eval.get("aggregate_by_target", {}),
            "overall_best_models": forecast_eval.get("overall_best_models", {}),
        },
    }

    sm_out = processed_dir / ev_cfg.get("output_summary", "evaluation_summary.json")
    with open(sm_out, "w") as f:
        json.dump(summary, f, indent=4, default=str)

    logger.info(f"  Evaluation summary saved → {sm_out}")
    logger.info(f"  Best solver: {ranking['best_solver']}")
    logger.info("Stage 9 complete.")
