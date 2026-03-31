import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.forecasting.registry import get_forecaster
from src.forecasting.selection import evaluate_models
from src.schemas.pandera_schemas import ForecastResultSchema, ModelEvaluationSchema

logger = logging.getLogger(__name__)

def generate_forecasts(config: Dict[str, Any] = None) -> None:
    """
    Executes the Stage 3 forecasting pipeline.
    Reads historical data, groups by subset, evaluates multiple models, 
    selects the best model per subset, predicts the configured horizon, 
    and validates output datasets against schemas.
    """
    if config is None:
        config = load_config()

    fc_cfg = config.get("forecasting", {})
    horizon = fc_cfg.get("horizon_periods", 6)
    min_history = fc_cfg.get("min_history_periods", 6)
    targets = fc_cfg.get("targets", ["inferred_demand", "inferred_supply", "balance"])
    
    # Enable a larger default set of models
    enabled_models_str = fc_cfg.get(
        "enabled_models", 
        ["Naive", "SeasonalNaive", "MovingAverage", "Drift", "SES", "Holt", "Theta", "HoltWinters", "RandomForest", "SimpleAverageEnsemble", "WeightedEnsemble"]
    )

    processed_dir = Path("data/processed")
    demand_cfg = config.get("demand_management", {})
    
    # Files
    signals_file = processed_dir / demand_cfg.get("output_signals_file", "historical_signals.parquet")
    balance_file = processed_dir / demand_cfg.get("output_balance_file", "historical_net_balance.parquet")
    
    if not signals_file.exists() or not balance_file.exists():
        logger.warning("Stage 3 requires Stage 2 outputs. Run demand management first.")
        return

    df_signals = pd.read_parquet(signals_file)
    df_balance = pd.read_parquet(balance_file)

    # Join the datasets for forecasting
    df_merged = pd.merge(df_signals, df_balance[['period', 'port', 'container_type', 'balance']], 
                         on=['period', 'port', 'container_type'], how='inner')

    # Prepare tracking lists
    all_evaluations = []
    all_forecasts = []

    # Iterate strictly over groups
    grouped = df_merged.groupby(['port', 'container_type'])
    for (port, ctype), group in grouped:
        group = group.sort_values('period')
        last_date = group['period'].max()

        # Handle future dates cleanly based on Pandas Datetime offsets
        future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq='ME')[1:]

        for target in targets:
            series = group[target]
            
            # Freshly instantiate models per segment to avoid state leakage
            models_to_run = []
            for m in enabled_models_str:
                try:
                    models_to_run.append(get_forecaster(m))
                except ValueError as e:
                    logger.warning(f"Skipping model {m} for {port}-{ctype}: {e}")
            
            # 1. Evaluate Model Performance on the historical segment
            evals = evaluate_models(models_to_run, series, min_history=min_history)
            
            best_model_name = None
            for e in evals:
                # Format evaluation for Parquet writing
                all_evaluations.append({
                    "port": port,
                    "container_type": ctype,
                    "target_variable": target,
                    "model_name": e["model_name"],
                    "mae": e.get("mae", 0.0),
                    "rmse": e.get("rmse", 0.0),
                    "smape": e.get("smape", 0.0),
                    "is_best_model": e["is_best_model"]
                })
                if e["is_best_model"]:
                    best_model_name = e["model_name"]

            # 2. Select best model object to produce final forecast
            if best_model_name is None:
                best_model_name = "Naive"
            
            active_model = get_forecaster(best_model_name)

            # 3. Fit on ALL available data to maximize freshness, then Predict the true Future
            fitted = active_model.fit(series)
            future_preds = fitted.predict(horizon)

            # 4. Record predictions matching ForecastResultSchema
            for i, p_val in enumerate(future_preds):
                map_target_to_type = {
                    "inferred_demand": "demand", 
                    "inferred_supply": "supply", 
                    "balance": "net_balance"
                }
                
                all_forecasts.append({
                    "target_period": future_dates[i],
                    "port": port,
                    "container_type": ctype,
                    "forecast_type": map_target_to_type.get(target, target),
                    "model_name": best_model_name,
                    "point_estimate": p_val,
                    "lower_bound": None,  # Can inject uncertainty bounds here later
                    "upper_bound": None
                })
                
    # Compile
    df_evals = pd.DataFrame(all_evaluations)
    df_preds = pd.DataFrame(all_forecasts)

    # Validate against schemas
    logger.info("Enforcing ModelEvaluationSchema...")
    df_evals = ModelEvaluationSchema.validate(df_evals)
    
    logger.info("Enforcing ForecastResultSchema...")
    df_preds = ForecastResultSchema.validate(df_preds)
    
    out_preds = processed_dir / fc_cfg.get("output_forecasts_file", "forecast_results.parquet")
    out_evals = processed_dir / fc_cfg.get("output_evaluations_file", "model_evaluations.parquet")

    df_preds.to_parquet(out_preds, index=False)
    df_evals.to_parquet(out_evals, index=False)

    logger.info(f"Forecasting complete. Wrote {len(df_preds)} rows to {out_preds}.")
