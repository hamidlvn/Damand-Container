import pytest
import pandas as pd
import numpy as np

from src.forecasting.metrics import evaluate_forecast, symmetric_mean_absolute_percentage_error
from src.forecasting.theta_model import ThetaForecaster
from src.forecasting.holt_winters import HoltWintersForecaster
from src.forecasting.random_forest import RandomForestTimeForecaster
from src.forecasting.ensemble import SimpleAverageEnsemble
from src.forecasting.selection import evaluate_models

def test_smape_zero_handling():
    # True pure zeros
    y_true = np.array([0.0, 10.0])
    y_pred = np.array([0.0, 8.0])
    
    smape = symmetric_mean_absolute_percentage_error(y_true, y_pred)
    assert smape >= 0.0

    metrics = evaluate_forecast(y_true, y_pred)
    assert 'smape' in metrics
    assert metrics['smape'] >= 0.0

def test_random_forest_lags():
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    rf = RandomForestTimeForecaster(n_lags=3)
    
    rf.fit(series)
    assert rf._fitted is True
    
    # Should predict the next 2 steps deterministically
    preds = rf.predict(2)
    assert len(preds) == 2

def test_ensemble_model():
    series = pd.Series([10.0, 12.0, 15.0, 14.0, 16.0, 20.0, 25.0])
    ens = SimpleAverageEnsemble()
    
    ens.fit(series)
    preds = ens.predict(3)
    assert len(preds) == 3

def test_naive_fallback():
    # Provide highly restricted sparse historical subset
    series = pd.Series([10.0, 12.0]) # Length 2
    
    theta = ThetaForecaster()
    hw = HoltWintersForecaster()
    
    results = evaluate_models([theta, hw], series, min_history=6)
    
    assert len(results) == 1
    assert results[0]['model_name'] == 'Naive'
    assert results[0]['is_best_model'] is True
