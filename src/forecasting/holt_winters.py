import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from src.forecasting.base import BaseForecaster
import warnings

class HoltWintersForecaster(BaseForecaster):
    """
    Holt-Winters Exponential Smoothing.
    Assumes monthly seasonal data without explicit trend if sparse.
    """
    
    def __init__(self, seasonal_periods: int = 12):
        self._seasonal_periods = seasonal_periods
        self._fitted_model = None

    @property
    def name(self) -> str:
        return "HoltWinters"

    def fit(self, series: pd.Series) -> 'HoltWintersForecaster':
        if len(series) < 2 * self._seasonal_periods:
            # Not enough data for robust seasonal HW, drop to simple exponential smoothing
            trend, seasonal = None, None
        else:
            trend, seasonal = 'add', 'add'
            
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._fitted_model = ExponentialSmoothing(
                    series, 
                    trend=trend, 
                    seasonal=seasonal, 
                    seasonal_periods=self._seasonal_periods
                ).fit()
        except Exception:
            self._fitted_model = None
            
        return self

    def predict(self, steps: int) -> pd.Series:
        if self._fitted_model is None:
            return pd.Series([0.0]*steps)
        
        forecast = self._fitted_model.forecast(steps)
        return forecast.fillna(0.0)
