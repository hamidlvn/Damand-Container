import pandera as pa
from pandera.typing import Series
import pandas as pd

# Pandera >= 0.17 uses DataFrameModel; SchemaModel is removed
_Base = pa.DataFrameModel

class RawIngestionSchema(_Base):
    """Pandera schema for raw CSV ingestion validation."""
    date: Series[str] = pa.Field(coerce=True)
    port: Series[str] = pa.Field(coerce=True, nullable=False)
    container_type: Series[str] = pa.Field(coerce=True, nullable=False)
    empty_out_teu: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=False)
    empty_in_teu: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=False)
    full_out_teu: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=True)
    full_in_teu: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=True)

    class Config:
        strict = False


class DemandSupplySignalSchema(_Base):
    """Pandera schema for Stage 2 demand/supply signals."""
    period: Series[str] = pa.Field(coerce=True)
    port: Series[str] = pa.Field(coerce=True, nullable=False)
    container_type: Series[str] = pa.Field(coerce=True, nullable=False)
    inferred_demand: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=False)
    inferred_supply: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=False)

    class Config:
        strict = False


class NetBalanceSchema(_Base):
    """Pandera schema for net balance records."""
    period: Series[str] = pa.Field(coerce=True)
    port: Series[str] = pa.Field(coerce=True, nullable=False)
    container_type: Series[str] = pa.Field(coerce=True, nullable=False)
    balance: Series[float] = pa.Field(coerce=True, nullable=False)
    is_shortage: Series[bool] = pa.Field(coerce=True, nullable=False)
    is_surplus: Series[bool] = pa.Field(coerce=True, nullable=False)
    criticality_score: Series[float] = pa.Field(ge=0.0, coerce=True, nullable=False)

    class Config:
        strict = False


class ForecastResultSchema(_Base):
    """Pandera schema for forecast output records."""
    target_period: Series[str] = pa.Field(coerce=True)
    port: Series[str] = pa.Field(coerce=True, nullable=False)
    container_type: Series[str] = pa.Field(coerce=True, nullable=False)
    forecast_type: Series[str] = pa.Field(coerce=True, nullable=False)
    model_name: Series[str] = pa.Field(coerce=True, nullable=False)
    point_estimate: Series[float] = pa.Field(coerce=True, nullable=False)
    lower_bound: Series[float] = pa.Field(coerce=True, nullable=True)
    upper_bound: Series[float] = pa.Field(coerce=True, nullable=True)

    class Config:
        strict = False


class ModelEvaluationSchema(_Base):
    """Pandera schema for model evaluation metrics."""
    port: Series[str] = pa.Field(coerce=True, nullable=False)
    container_type: Series[str] = pa.Field(coerce=True, nullable=False)
    target_variable: Series[str] = pa.Field(coerce=True, nullable=False)
    model_name: Series[str] = pa.Field(coerce=True, nullable=False)
    mae: Series[float] = pa.Field(coerce=True, nullable=False)
    rmse: Series[float] = pa.Field(coerce=True, nullable=False)
    smape: Series[float] = pa.Field(coerce=True, nullable=False)
    is_best_model: Series[bool] = pa.Field(coerce=True, nullable=False)

    class Config:
        strict = False
