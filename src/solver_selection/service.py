import logging
import json
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.schemas.core import StructuredProblem, SolverStrategy
from src.solver_selection.rules import extract_features, SelectionRules

logger = logging.getLogger(__name__)


def select_solver(config: Dict[str, Any] = None) -> None:
    """
    Orchestrates Stage 7: Loads the StructuredProblem artifact, extracts problem
    complexity features, applies the deterministic rule engine, and saves the
    resulting SolverStrategy to data/processed/.
    """
    if config is None:
        config = load_config()

    ss_cfg = config.get("solver_selection", {})
    processed_dir = Path("data/processed")

    prob_cfg = config.get("problem_builder", {})
    problem_file = processed_dir / prob_cfg.get("output_problem_file", "structured_problem.json")

    logger.info("Stage 7 – Solver Selection starting.")

    if not problem_file.exists():
        logger.error("Stage 7 requires a StructuredProblem artifact from Stage 6. Aborting.")
        return

    with open(problem_file, "r") as f:
        sp = StructuredProblem.model_validate_json(f.read())

    # 1. Extract scalar complexity features
    features = extract_features(sp)
    logger.info(
        f"Features extracted — ports={features.num_ports}, "
        f"periods={features.num_time_periods}, arcs={features.num_arcs}, "
        f"soft_budget={features.has_soft_budget}, "
        f"port_overrides={features.has_per_port_service_override}"
    )

    # 2. Apply rule engine
    limits = ss_cfg.get("limits", {})
    rules = SelectionRules(limits)
    decision = rules.select(features)

    # 3. Assemble SolverStrategy
    strategy = SolverStrategy(
        problem_id=sp.problem_id,
        **decision
    )

    logger.info(
        f"Strategy decided: {strategy.execution_mode.upper()} → "
        f"{strategy.selected_solver} | hint={strategy.runtime_hint}"
    )
    logger.info(f"Reasoning: {strategy.reasoning}")

    # 4. Persist artifact
    out_file = processed_dir / ss_cfg.get("output_strategy_file", "solver_strategy.json")
    with open(out_file, "w") as f:
        f.write(strategy.model_dump_json(indent=4))

    logger.info(f"Stage 7 complete. SolverStrategy saved to {out_file}.")
