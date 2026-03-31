import pandas as pd
from src.forecasting.base import BaseForecaster

class MovingAverageForecaster(BaseForecaster):
    """Naive 3-month average baseline."""
    def __init__(self, window: int = 3, **kwargs):
        self._window = window
        self._avg_val = 0.0
        
    @property
    def name(self) -> str:
        return "MovingAverage"
        
    def fit(self, series: pd.Series) -> 'MovingAverageForecaster':
        if len(series) == 0:
            self._avg_val = 0.0
        elif len(series) < self._window:
            self._avg_val = series.mean()
        else:
            self._avg_val = series.iloc[-self._window:].mean()
        return self

    def predict(self, steps: int) -> pd.Series:
        return pd.Series([float(self._avg_val)] * steps)
