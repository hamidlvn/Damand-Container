import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.constraints.builder import ConstraintBuilder
from src.constraints.validation import validate_constraint_set

logger = logging.getLogger(__name__)

def generate_constraints(config: Dict[str, Any] = None) -> None:
    """
    Orchestrates Stage 4: Extrapolating the generic configuration parameters 
    across the active node network (pulled directly from recent Forecasts),
    validates the assumptions structure, and writes to a structured json definition.
    """
    if config is None:
        config = load_config()

    constrained_cfg = config.get("constraints", {})
    processed_dir = Path("data/processed")
    
    # Needs Forecast results to determine the exact required ports to constrain
    fc_cfg = config.get("forecasting", {})
    forecasts_file = processed_dir / fc_cfg.get("output_forecasts_file", "forecast_results.parquet")

    logger.info(f"Starting Constraints Parameterization Phase. Sifting from {forecasts_file}")
    
    if not forecasts_file.exists():
        logger.warning("Stage 4 requires Stage 3 outputs. Generating universal fallback ports list.")
        # If forecasts are missing but we want to test functionality independently
        unique_ports = {"FallbackPort_A", "FallbackPort_B"}
    else:
        # Load forecasts simply to extract the active nodes list
        df_forecasts = pd.read_parquet(forecasts_file)
        unique_ports = set(df_forecasts['port'].unique())

    # Build Constraints explicitly over explicit active network scope
    builder = ConstraintBuilder(config)
    port_constraints = builder.build_port_constraints(unique_ports)
    cset = builder.build_global_constraints(port_constraints)

    # 4. Run explicit Validation logic guaranteeing solvers don't implode
    logger.info("Enforcing Constraints logical consistency validation...")
    validate_constraint_set(cset)

    # Output to the structured standard
    out_file = processed_dir / constrained_cfg.get("output_constraints_file", "business_constraints.json")
    
    # Save using Pydantic's JSON standard dump mechanism
    with open(out_file, "w") as f:
        f.write(cset.model_dump_json(indent=4))
        
    logger.info(f"Stage 4 Constraints layer complete. Valid Constraints saved to {out_file}.")
