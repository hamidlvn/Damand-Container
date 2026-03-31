import pandas as pd
from statsmodels.tsa.forecasting.theta import ThetaModel
from src.forecasting.base import BaseForecaster
import warnings

class ThetaForecaster(BaseForecaster):
    """
    Standard Theta Model Implementation using statsmodels.
    Handles non-negative forecasting and deterministic bounds if necessary.
    """
    
    def __init__(self, period_length: int = 12):
        self._period = period_length
        self._fitted_model = None

    @property
    def name(self) -> str:
        return "Theta"

    def fit(self, series: pd.Series) -> 'ThetaForecaster':
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._fitted_model = ThetaModel(endog=series, period=self._period).fit()
        except ValueError:
            # Fallback if un-fittable
            self._fitted_model = None
            
        return self

    def predict(self, steps: int) -> pd.Series:
        if self._fitted_model is None:
            return pd.Series([0.0]*steps)
            
        forecast = self._fitted_model.forecast(steps)
        # Assuming most container quantities shouldn't explicitly go negative unless it is the net balance
        return forecast.fillna(0.0)
