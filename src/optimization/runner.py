import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from src.utils.config import load_config
from src.schemas.core import StructuredProblem, SolverStrategy, SolverResult
from src.optimization.heuristic_solver import HeuristicSolver
from src.optimization.milp_solver import MILPSolver

logger = logging.getLogger(__name__)

SOLVERS = {
    "Heuristic": HeuristicSolver(),
    "MILP":      MILPSolver(),
}


def run_optimization(config: Dict[str, Any] = None) -> None:
    """
    Stage 8 orchestrator:
      1. Load StructuredProblem + SolverStrategy artifacts from disk.
      2. Dispatch to the correct solver(s) per strategy execution_mode.
      3. Fall back automatically if the primary solver fails.
      4. Persist each SolverResult as a separate JSON artifact.
    """
    if config is None:
        config = load_config()

    processed_dir = Path("data/processed")

    prob_file = processed_dir / config.get("problem_builder", {}).get(
        "output_problem_file", "structured_problem.json"
    )
    strat_file = processed_dir / config.get("solver_selection", {}).get(
        "output_strategy_file", "solver_strategy.json"
    )

    logger.info("Stage 8 – Optimization Solvers starting.")

    if not prob_file.exists() or not strat_file.exists():
        logger.error("Stage 8 requires Stage 6 (problem) and Stage 7 (strategy) artifacts.")
        return

    with open(prob_file, "r") as f:
        sp = StructuredProblem.model_validate_json(f.read())

    with open(strat_file, "r") as f:
        strategy = SolverStrategy.model_validate_json(f.read())

    results: List[SolverResult] = _dispatch(sp, strategy)

    for result in results:
        out_name = f"solver_result_{result.solver_name.lower()}.json"
        out_path = processed_dir / out_name
        with open(out_path, "w") as f:
            f.write(result.model_dump_json(indent=4))
        logger.info(
            f"  [{result.solver_name}] status={result.status} | "
            f"obj={result.objective_value:.2f} | "
            f"svc_level={result.service_level:.2%} | "
            f"cost={result.total_cost:.2f} | "
            f"moves={len(result.decisions)} | "
            f"time={result.solve_time_seconds}s → {out_path}"
        )

    logger.info("Stage 8 complete.")


# ── internal dispatch ──────────────────────────────────────────────────────────

def _dispatch(sp: StructuredProblem, strategy: SolverStrategy) -> List[SolverResult]:
    """Runs solvers per execution_mode; handles fallback transparently."""
    results: List[SolverResult] = []

    solvers_to_run = strategy.selected_solver

    for solver_name in solvers_to_run:
        solver = SOLVERS.get(solver_name)
        if solver is None:
            logger.warning(f"Unknown solver '{solver_name}' skipped.")
            continue

        logger.info(f"Running {solver_name} solver …")
        result = solver.solve(sp)

        if result.status in ("failed", "infeasible") and strategy.fallback_solver:
            fallback_name = strategy.fallback_solver
            if fallback_name not in solvers_to_run:
                logger.warning(
                    f"{solver_name} returned '{result.status}'. "
                    f"Trying fallback: {fallback_name}."
                )
                fallback = SOLVERS.get(fallback_name)
                if fallback:
                    result = fallback.solve(sp)
                    result.diagnostics["fallback_used"] = fallback_name

        results.append(result)

    return results
