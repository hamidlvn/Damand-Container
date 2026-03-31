from typing import Type, Dict
from src.forecasting.base import BaseForecaster
from src.forecasting.naive import NaiveForecaster
from src.forecasting.seasonal_naive import SeasonalNaiveForecaster
from src.forecasting.moving_average import MovingAverageForecaster
from src.forecasting.drift import DriftForecaster
from src.forecasting.ses import SESForecaster
from src.forecasting.holt import HoltForecaster
from src.forecasting.theta_model import ThetaForecaster
from src.forecasting.holt_winters import HoltWintersForecaster
from src.forecasting.random_forest import RandomForestTimeForecaster
from src.forecasting.ensemble import SimpleAverageEnsemble, WeightedEnsemble

MODEL_REGISTRY: Dict[str, Type[BaseForecaster]] = {
    "Naive": NaiveForecaster,
    "SeasonalNaive": SeasonalNaiveForecaster,
    "MovingAverage": MovingAverageForecaster,
    "Drift": DriftForecaster,
    "SES": SESForecaster,
    "Holt": HoltForecaster,
    "Theta": ThetaForecaster,
    "HoltWinters": HoltWintersForecaster,
    "RandomForest": RandomForestTimeForecaster,
    "SimpleAverageEnsemble": SimpleAverageEnsemble,
    "WeightedEnsemble": WeightedEnsemble
}

def get_forecaster(model_name: str, **kwargs) -> BaseForecaster:
    """Returns an instantiated forecaster from the exact model name string."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown forecasting model: {model_name}")
    return MODEL_REGISTRY[model_name](**kwargs)
