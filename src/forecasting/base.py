from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class BaseForecaster(ABC):
    """
    Abstract Base Class for all forecasting models.
    Enforces a standardized contract for fitting and predicting.
    """
    
    @abstractmethod
    def __init__(self, **kwargs):
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the unique identifier for the model."""
        pass

    @abstractmethod
    def fit(self, series: pd.Series) -> 'BaseForecaster':
        """Fits the model to a historical Target Pandas Series."""
        pass

    @abstractmethod
    def predict(self, steps: int) -> pd.Series:
        """Generates future forecasts for `steps` periods."""
        pass

class FallbackNaive(BaseForecaster):
    """
    Naive baseline fallback for extremely short/sparse time-series 
    where complex models fail. Merely returns the last observed 
    value or mean.
    """
    def __init__(self, use_mean: bool = False):
        self._use_mean = use_mean
        self._fallback_value = 0.0
        
    @property
    def name(self) -> str:
        return "NaiveFallback"
        
    def fit(self, series: pd.Series) -> 'FallbackNaive':
        if len(series) == 0:
            self._fallback_value = 0.0
        elif self._use_mean:
            self._fallback_value = series.mean()
        else:
            self._fallback_value = series.iloc[-1]
        return self

    def predict(self, steps: int) -> pd.Series:
        return pd.Series([self._fallback_value] * steps)
