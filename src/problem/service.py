import logging
import json
import uuid
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.schemas.core import ConstraintSet, CapacityContext
from src.problem.builder import ProblemBuilder
from src.problem.validation import validate_structured_problem

logger = logging.getLogger(__name__)

def generate_problem(config: Dict[str, Any] = None) -> None:
    """
    Orchestrates Stage 6: The core integration step loading all disparate Forecasts, Capacity Graph Limits,
    and Business Constraints into a strictly matrix-indexed Pydantic formulation structured for Solvers.
    """
    if config is None:
        config = load_config()

    prob_cfg = config.get("problem_builder", {})
    processed_dir = Path("data/processed")
    
    # Needs Forecast results
    fc_cfg = config.get("forecasting", {})
    forecasts_file = processed_dir / fc_cfg.get("output_forecasts_file", "forecast_results.parquet")
    
    # Needs Constraints
    con_cfg = config.get("constraints", {})
    constraints_file = processed_dir / con_cfg.get("output_constraints_file", "business_constraints.json")
    
    # Needs Capacity
    cap_cfg = config.get("capacity", {})
    capacity_file = processed_dir / cap_cfg.get("output_capacity_file", "transport_capacity.json")

    logger.info(f"Starting Mathematical Problem Formatting Orchestrator.")
    if not forecasts_file.exists() or not constraints_file.exists() or not capacity_file.exists():
        logger.error("Stage 6 execution HALTED. Upstream data dependencies inherently missing.")
        return

    df_forecasts = pd.read_parquet(forecasts_file)
    
    with open(constraints_file, "r") as f:
        cset = ConstraintSet.model_validate_json(f.read())
        
    with open(capacity_file, "r") as f:
        cctx = CapacityContext.model_validate_json(f.read())

    # Build the Transportation Network mapping
    builder = ProblemBuilder(df_forecasts, cset, cctx)
    pid = prob_cfg.get("problem_id_prefix", "PROB-") + str(uuid.uuid4())[:8]
    
    # Assemble structures mapped cleanly
    problem = builder.build_problem(problem_id=pid)

    # Assure constraint bounds matching logic matrices natively aligns safely 
    logger.info("Enforcing Matrix Dimensional logic constraints...")
    validate_structured_problem(problem)

    # Output to the structured standard
    out_file = processed_dir / prob_cfg.get("output_problem_file", "structured_problem.json")
    
    with open(out_file, "w") as f:
        f.write(problem.model_dump_json(indent=4))
        
    # Exposing logging sizes explicitly summarizing matrices
    num_ports = len(problem.ports)
    num_times = len(problem.time_periods)
    
    logger.info(f"Stage 6 Structured Integration complete.")
    logger.info(f"Total Dimension bounds parsed: [{num_ports}] Ports mapped across [{num_times}] Temporal sequence indices.")
    logger.info(f"Generated strict output cleanly isolated safely to {out_file}.")
