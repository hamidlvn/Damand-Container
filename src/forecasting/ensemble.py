import pandas as pd
import numpy as np
from typing import List
from src.forecasting.base import BaseForecaster
from src.forecasting.theta_model import ThetaForecaster
from src.forecasting.holt_winters import HoltWintersForecaster
from src.forecasting.random_forest import RandomForestTimeForecaster

class SimpleAverageEnsemble(BaseForecaster):
    """
    Computes simple mean average ensemble across a set of instantiated forecasters.
    Requires that fit strategy is managed externally or via passing fit models.
    """
    def __init__(self, models: List[BaseForecaster] = None, **kwargs):
        if models is None:
            # Default instantiation, pick robust subsets
            models = [
                ThetaForecaster(),
                HoltWintersForecaster(),
                RandomForestTimeForecaster()
            ]
        self._models = models

    @property
    def name(self) -> str:
        return "SimpleAverageEnsemble"

    def fit(self, series: pd.Series) -> 'SimpleAverageEnsemble':
        for model in self._models:
            model.fit(series)
        return self

    def predict(self, steps: int) -> pd.Series:
        all_preds = []
        for model in self._models:
            preds = model.predict(steps)
            all_preds.append(preds.values)
            
        if not all_preds:
            return pd.Series([0.0] * steps)
            
        df_preds = pd.DataFrame(all_preds)
        mean_preds = df_preds.mean(axis=0)
        return pd.Series(mean_preds.values)

class WeightedEnsemble(BaseForecaster):
    """
    Computes a weighted ensemble. A true rigorous weighting requires in-sample 
    validation error tracking. Without it passed at instantiation, falls back to equal uniform weights.
    """
    def __init__(self, models: List[BaseForecaster] = None, weights: List[float] = None, **kwargs):
        if models is None:
            models = [
                ThetaForecaster(),
                HoltWintersForecaster(),
                RandomForestTimeForecaster()
            ]
        self._models = models
        self._weights = weights

    @property
    def name(self) -> str:
        return "WeightedEnsemble"

    def fit(self, series: pd.Series) -> 'WeightedEnsemble':
        for model in self._models:
            model.fit(series)
        return self

    def predict(self, steps: int) -> pd.Series:
        all_preds = []
        for model in self._models:
            preds = model.predict(steps)
            all_preds.append(preds.values)
            
        if not all_preds:
            return pd.Series([0.0] * steps)
            
        df_preds = pd.DataFrame(all_preds)
        if self._weights is not None and sum(self._weights) > 0 and len(self._weights) == len(self._models):
            # Normalize just in case
            w = np.array(self._weights) / sum(self._weights)
            weighted_preds = np.average(df_preds.values, axis=0, weights=w)
            return pd.Series(weighted_preds)
        else:
            # Fallback to simple average
            return pd.Series(df_preds.mean(axis=0).values)
