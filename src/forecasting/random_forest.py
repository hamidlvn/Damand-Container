import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from src.forecasting.base import BaseForecaster
import warnings

class RandomForestTimeForecaster(BaseForecaster):
    """
    Supervised Learning approach to Time Series using Random Forest.
    Features engineered via sliding window lags.
    """
    
    def __init__(self, n_lags: int = 3, random_state: int = 42):
        self._n_lags = n_lags
        self._model = RandomForestRegressor(n_estimators=100, random_state=random_state)
        self._fitted = False
        self._last_observed = None

    @property
    def name(self) -> str:
        return "RandomForest"

    def _create_supervised_features(self, series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        """Convert time series to supervised learning lags."""
        vals = series.values
        X, y = [], []
        for i in range(len(vals) - self._n_lags):
            X.append(vals[i : i + self._n_lags])
            y.append(vals[i + self._n_lags])
            
        return np.array(X), np.array(y)

    def fit(self, series: pd.Series) -> 'RandomForestTimeForecaster':
        if len(series) <= self._n_lags + 1:
            self._fitted = False
            return self
            
        X, y = self._create_supervised_features(series)
        
        if len(X) > 0:
            self._model.fit(X, y)
            self._fitted = True
            self._last_observed = series.values[-self._n_lags:]
            
        return self

    def predict(self, steps: int) -> pd.Series:
        if not self._fitted or self._last_observed is None:
            return pd.Series([0.0]*steps)
            
        predictions = []
        current_lags = list(self._last_observed)
        
        for _ in range(steps):
            x_input = np.array(current_lags[-self._n_lags:]).reshape(1, -1)
            pred = self._model.predict(x_input)[0]
            predictions.append(pred)
            current_lags.append(pred)
            
        return pd.Series(predictions)
