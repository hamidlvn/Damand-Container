import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Set, List
from datetime import date

from src.utils.config import load_config
from src.capacity.generator import VoyageGenerator
from src.capacity.validation import validate_capacity_context

logger = logging.getLogger(__name__)

def generate_capacity(config: Dict[str, Any] = None) -> None:
    """
    Orchestrates Stage 5: Loading the transport requirements and mapping
    a fully valid graph logic across all future Forecasted Horizons into a structural JSON for the Solver layers.
    """
    if config is None:
        config = load_config()

    cap_cfg = config.get("capacity", {})
    processed_dir = Path("data/processed")
    
    fc_cfg = config.get("forecasting", {})
    forecasts_file = processed_dir / fc_cfg.get("output_forecasts_file", "forecast_results.parquet")

    logger.info(f"Starting Capacity Network Mapping. Scanning active nodes and periods.")
    
    unique_ports: Set[str] = set()
    periods: List[date] = []
    
    # We must derive active ports AND temporal forecast horizon points
    if not forecasts_file.exists():
        logger.warning("Stage 5 prefers Stage 3 outputs. Reserving universal mock network nodes mapping 1 period offset.")
        unique_ports = {"Fallback_A", "Fallback_B", "Fallback_C"}
        periods = [pd.Timestamp.now().date()]
    else:
        df_forecasts = pd.read_parquet(forecasts_file)
        unique_ports = set(df_forecasts['port'].unique())
        
        # Pull distinct target forecast dates explicitly
        sorted_dates = sorted(df_forecasts['target_period'].unique())
        # Convert pd.Timestamp to python dates
        periods = [pd.Timestamp(dt).date() for dt in sorted_dates]

    # Initialize the generator engine with parameter configuration
    generator = VoyageGenerator(config)
    
    # Builds fully-synthesized Leg projections tracking (O,D,Departure,Arrival,Cap,Cost) over time
    voyage_legs = generator.generate_voyage_legs(unique_ports, periods)
    ctx = generator.build_context(voyage_legs)

    # Assure Logical Bound stability explicitly testing for negative-time Paradoxes or Null values
    logger.info("Enforcing Voyage Leg logic bounds...")
    validate_capacity_context(ctx)

    # Output to the structured Pydantic standard JSON
    out_file = processed_dir / cap_cfg.get("output_capacity_file", "transport_capacity.json")
    
    with open(out_file, "w") as f:
        f.write(ctx.model_dump_json(indent=4))
        
    logger.info(f"Stage 5 Capacity Modeling complete. {len(voyage_legs)} dynamic legs across {len(periods)} periods output validated to {out_file}.")
