import pytest
import pandas as pd
import numpy as np
from src.ingestion.loader import standardize_columns, validate_required_columns, clean_and_fill_missing

def test_standardize_columns():
    df = pd.DataFrame({"Date": ["2018-01-01"], " PORT_NAME ": ["Genoa"]})
    clean_df = standardize_columns(df)
    assert list(clean_df.columns) == ["date", "port_name"]

def test_validate_required_columns():
    df = pd.DataFrame({"date": ["2018-01-01"], "port": ["Genoa"]})
    required = ["Date", "Port"]
    
    # Should not raise
    validate_required_columns(df, required)
    
    # Should raise missing container_type
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_required_columns(df, ["Date", "Port", "Container_Type"])

def test_clean_and_fill_missing():
    # Setup dataframe with missing and invalid data
    df = pd.DataFrame({
        "date": ["2018-01-01", "invalid_date", None],
        "empty_out_teu": [10.0, np.nan, "10"],
        "empty_in_teu": [5.0, None, 2.0]
    })
    
    cleaned = clean_and_fill_missing(df.copy())
    
    # invalid date row and null date row should be dropped
    assert len(cleaned) == 1
    
    # NA values should be coerced/filled
    df2 = pd.DataFrame({
        "date": ["2018-01-01", "2018-01-02"],
        "empty_out_teu": [10.0, np.nan],
        "empty_in_teu": ["xx", 5.0]
    })
    cleaned2 = clean_and_fill_missing(df2.copy())
    
    assert len(cleaned2) == 2
    assert cleaned2.iloc[1]["empty_out_teu"] == 0.0 # Filled from NaN
    assert cleaned2.iloc[0]["empty_in_teu"] == 0.0 # Non-numeric coerced to NaN, then filled to 0.0
