import pandas as pd
import logging

logger = logging.getLogger(__name__)

def aggregate_historical_data(df: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """
    Aggregates the raw daily (or arbitrary) historical data into a specific 
    time frequency (e.g., 'ME' for Month End).
    
    Groups by explicitly by Time frequency, Port, and Container_Type.
    Sums the numeric TEU variables.
    """
    if df.empty:
        return df
        
    required_cols = {'date', 'port', 'container_type', 'empty_out_teu', 'empty_in_teu'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Cannot aggregate. Missing columns: {missing}")
        
    # Ensure date is a datetime object just in case
    df['date'] = pd.to_datetime(df['date'])
    
    logger.info(f"Aggregating dataset to frequency: {freq}")
    
    # Use pandas Grouper with the target frequency
    agg_df = df.groupby([
        pd.Grouper(key='date', freq=freq),
        'port',
        'container_type'
    ]).agg({
        'empty_out_teu': 'sum',
        'empty_in_teu': 'sum',
        'full_out_teu': 'sum',
        'full_in_teu': 'sum'
    }).reset_index()
    
    logger.info(f"Aggregated {len(df)} raw rows down to {len(agg_df)} period rows.")
    
    return agg_df

