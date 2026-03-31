import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.demand.aggregation import aggregate_historical_data
from src.demand.signals import compute_historical_signals, compute_net_balance
from src.demand.priority import compute_priority_score
from src.schemas.pandera_schemas import DemandSupplySignalSchema, NetBalanceSchema

logger = logging.getLogger(__name__)

def process_demand_layer(cleaned_data_path: str = None, config: Dict[str, Any] = None) -> None:
    """
    Orchestrates Stage 2 (Demand Management).
    Reads the validated historical output of Stage 1, applies aggregation, 
    computes signals, calculates net balance and priority, validates to schemas, 
    and exports the partitioned modules into data/processed/.
    """
    if config is None:
        config = load_config()

    demand_cfg = config.get("demand_management", {})
    freq = demand_cfg.get("aggregation_level", "ME")
    weight = demand_cfg.get("priority_weight", 1.0)
    
    processed_dir = Path("data/processed")
    if cleaned_data_path is None:
        ingestion_cfg = config.get("ingestion", {})
        cleaned_data_path = processed_dir / ingestion_cfg.get("processed_file_name", "cleaned_history.parquet")

    logger.info(f"Starting Demand Management Processing. Reading from {cleaned_data_path}")
    
    if not Path(cleaned_data_path).exists():
        raise FileNotFoundError(f"Missing Stage 1 output: {cleaned_data_path}")

    # 1. Read cleaned data
    df_raw = pd.read_parquet(cleaned_data_path)
    
    if df_raw.empty:
        logger.warning("No data found to process for Demand module.")
        return

    # 2. Extract & Aggregate time-series frequencies
    df_agg = aggregate_historical_data(df_raw, freq)

    # 3. Compute business signals (demand, supply)
    signals_df = compute_historical_signals(df_agg)
    
    # 4. Strict Schema Validation for Signals
    logger.info("Enforcing DemandSupplySignalSchema...")
    signals_df = DemandSupplySignalSchema.validate(signals_df)

    # 5. Compute net balance & classification 
    balance_df = compute_net_balance(signals_df)

    # 6. Compute priority criticality
    policy_df = compute_priority_score(balance_df, weight)
    
    # 7. Strict Schema Validation for final NetBalance output
    logger.info("Enforcing NetBalanceSchema...")
    policy_df = NetBalanceSchema.validate(policy_df)

    # Export Processed Artefacts
    out_sig = processed_dir / demand_cfg.get("output_signals_file", "historical_signals.parquet")
    out_bal = processed_dir / demand_cfg.get("output_balance_file", "historical_net_balance.parquet")
    
    signals_df.to_parquet(out_sig, index=False)
    policy_df.to_parquet(out_bal, index=False)
    
    logger.info(f"Demand layer complete. Signals saved to {out_sig}. Net Balance saved to {out_bal}.")
