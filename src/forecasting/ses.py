import pandas as pd
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from src.forecasting.base import BaseForecaster
import warnings

class SESForecaster(BaseForecaster):
    """Simple Exponential Smoothing."""
    def __init__(self, **kwargs):
        self._fitted_model = None
        self._fallback_val = 0.0
        
    @property
    def name(self) -> str:
        return "SES"
        
    def fit(self, series: pd.Series) -> 'SESForecaster':
        if len(series) < 3:
            self._fitted_model = None
            self._fallback_val = float(series.mean()) if len(series) > 0 else 0.0
            return self
            
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._fitted_model = SimpleExpSmoothing(series, initialization_method="estimated").fit()
        except Exception:
            self._fitted_model = None
            self._fallback_val = float(series.mean())
            
        return self

    def predict(self, steps: int) -> pd.Series:
        if self._fitted_model is None:
            return pd.Series([float(self._fallback_val)] * steps)
        
        forecast = self._fitted_model.forecast(steps)
        return forecast.fillna(0.0)
