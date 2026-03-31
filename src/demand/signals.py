import pandas as pd
from typing import Tuple

def compute_historical_signals(agg_df: pd.DataFrame) -> pd.DataFrame:
    """
    Translates raw TEU variables into standard business terminology:
    - inferred_demand = empty_out_teu
    - inferred_supply = empty_in_teu
    """
    signals = agg_df.copy()
    
    # Rename Date to Period to match Schema requirements
    if 'date' in signals.columns:
        signals = signals.rename(columns={'date': 'period'})
        
    signals['inferred_demand'] = signals['empty_out_teu']
    signals['inferred_supply'] = signals['empty_in_teu']
    
    # Drop the explicit operational operational TEU fields from the final signal view 
    # to standardize the data contract layer
    cols_to_keep = ['period', 'port', 'container_type', 'inferred_demand', 'inferred_supply']
    return signals[cols_to_keep]

def compute_net_balance(signals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the net balance based on supply and demand signals.
    Also computes the shortage, surplus, and balanced flags.
    
    Formula: net_balance = historical_supply - historical_demand
    """
    bal = signals_df.copy()
    
    bal['balance'] = bal['inferred_supply'] - bal['inferred_demand']
    
    bal['is_shortage'] = bal['balance'] < 0
    bal['is_surplus'] = bal['balance'] > 0
    bal['balance_status'] = bal['balance'].apply(
        lambda x: "shortage" if x < 0 else ("surplus" if x > 0 else "balanced")
    )
    
    return bal
