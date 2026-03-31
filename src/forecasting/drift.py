import pandas as pd
from src.forecasting.base import BaseForecaster

class DriftForecaster(BaseForecaster):
    """Drift baseline: connects first and last observation."""
    def __init__(self, **kwargs):
        self._last_val = 0.0
        self._slope = 0.0
        
    @property
    def name(self) -> str:
        return "Drift"
        
    def fit(self, series: pd.Series) -> 'DriftForecaster':
        n = len(series)
        if n == 0:
            self._last_val = 0.0
            self._slope = 0.0
        elif n == 1:
            self._last_val = series.iloc[-1]
            self._slope = 0.0
        else:
            self._last_val = series.iloc[-1]
            self._slope = (series.iloc[-1] - series.iloc[0]) / (n - 1)
        return self

    def predict(self, steps: int) -> pd.Series:
        preds = [float(self._last_val + self._slope * i) for i in range(1, steps + 1)]
        return pd.Series(preds)
