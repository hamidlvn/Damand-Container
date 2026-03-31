import pandas as pd
from src.forecasting.base import BaseForecaster

class SeasonalNaiveForecaster(BaseForecaster):
    """Seasonal Naive: y_t = y_{t-s} (s=12 by default for monthly)"""
    def __init__(self, seasonal_periods: int = 12, **kwargs):
        self._s = seasonal_periods
        self._history = []
        
    @property
    def name(self) -> str:
        return "SeasonalNaive"
        
    def fit(self, series: pd.Series) -> 'SeasonalNaiveForecaster':
        if len(series) < self._s:
            # Fallback to simple naive if history is insufficient
            if len(series) > 0:
                val = series.iloc[-1]
                self._history = [val] * self._s
            else:
                self._history = [0.0] * self._s
        else:
            self._history = series.iloc[-self._s:].values.tolist()
        return self

    def predict(self, steps: int) -> pd.Series:
        preds = []
        for i in range(steps):
            preds.append(float(self._history[i % self._s]))
        return pd.Series(preds)
