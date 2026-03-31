import pandas as pd

def compute_priority_score(net_balance_df: pd.DataFrame, weight_factor: float = 1.0) -> pd.DataFrame:
    """
    Computes a simple, deterministic priority score based on shortage magnitude.
    A positive score indicates high priority (critical shortage).
    Surplus or balanced rows get a score of 0.0.
    
    Formula: criticality_score = abs(min(0, net_balance)) * weight_factor
    """
    df_scored = net_balance_df.copy()
    
    def score_row(balance: float) -> float:
        if balance < 0:
            return abs(balance) * weight_factor
        return 0.0
        
    df_scored['criticality_score'] = df_scored['balance'].apply(score_row)
    
    return df_scored
