import numpy as np

def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return np.mean(np.abs(y_true - y_pred))

def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return np.sqrt(np.mean(np.square(y_true - y_pred)))

def symmetric_mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    sMAPE metric resilient to zero-value observations, returning robust percentages.
    Implementation bounded between 0 and 200%.
    """
    denominator = (np.abs(y_true) + np.abs(y_pred))
    
    # Handle pure zero cases safely (0/0 -> 0 error)
    diff = np.abs(y_true - y_pred)
    result = np.zeros_like(diff)
    
    mask = denominator > 0
    result[mask] = diff[mask] / (denominator[mask] / 2.0)
    
    return np.mean(result) * 100.0

def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Computes a standardized suite of forecast accuracy metrics."""
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": root_mean_squared_error(y_true, y_pred),
        "smape": symmetric_mean_absolute_percentage_error(y_true, y_pred)
    }
