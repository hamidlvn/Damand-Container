import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from src.forecasting.metrics import evaluate_forecast

def time_series_train_test_split(series: pd.Series, test_size: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Strict chronological split. No random reshuffling."""
    split_point = len(series) - test_size
    return series.iloc[:split_point], series.iloc[split_point:]

def evaluate_models(models: list, series: pd.Series, min_history: int = 6) -> list:
    """
    Evaluates a set of initialized forecasters against a time-series.
    Handles naive fallback if history is too sparse.
    Returns a unified list of evaluation dictionaries.
    """
    results = []
    
    if len(series) <= min_history:
        # Direct Fallback path, no complex evaluation needed
        return [{
            "model_name": "Naive",
            "mae": 0.0,
            "rmse": 0.0,
            "smape": 0.0,
            "is_best_model": True
        }]
    
    # Simple split strategy
    train, test = time_series_train_test_split(series, test_size=min_history//2)
    
    best_smape = float('inf')
    evals = []
    
    for model in models:
        # Fit on train
        fitted = model.fit(train)
        preds = fitted.predict(len(test))
        
        # Calculate standardized metrics
        metrics = evaluate_forecast(test.values, preds.values)
        metrics["model_name"] = model.name
        metrics["is_best_model"] = False
        evals.append(metrics)
        
        if metrics["smape"] < best_smape:
            best_smape = metrics["smape"]
            
    # Mark the best model
    for e in evals:
        if e["smape"] == best_smape:
            e["is_best_model"] = True
            break
            
    return evals
