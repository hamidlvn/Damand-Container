import pandas as pd
from typing import Optional
from src.forecasting.base import BaseForecaster

class NaiveForecaster(BaseForecaster):
    """Naive baseline: y_t = y_{t-1}"""
    def __init__(self, **kwargs):
        self._last_val = 0.0
        
    @property
    def name(self) -> str:
        return "Naive"
        
    def fit(self, series: pd.Series) -> 'NaiveForecaster':
        if len(series) > 0:
            self._last_val = series.iloc[-1]
        else:
            self._last_val = 0.0
        return self

    def predict(self, steps: int) -> pd.Series:
        return pd.Series([float(self._last_val)] * steps)
