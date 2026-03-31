import pytest
import pandas as pd
from src.demand.aggregation import aggregate_historical_data
from src.demand.signals import compute_historical_signals, compute_net_balance
from src.demand.priority import compute_priority_score

@pytest.fixture
def mock_clean_data():
    return pd.DataFrame({
        'date': ['2018-01-01', '2018-01-15', '2018-02-01', '2018-01-01'],
        'port': ['Genoa', 'Genoa', 'Genoa', 'Naples'],
        'container_type': ['20ST', '20ST', '20ST', '40HC'],
        'empty_out_teu': [10.0, 5.0, 20.0, 0.0],
        'empty_in_teu': [8.0, 2.0, 25.0, 10.0],
        'full_out_teu': [0.0, 0.0, 0.0, 0.0],
        'full_in_teu': [0.0, 0.0, 0.0, 0.0]
    })

def test_aggregation_correctness(mock_clean_data):
    # Testing "ME" (Month End) aggregation for Genoa 20ST
    agg_df = aggregate_historical_data(mock_clean_data, freq='ME')
    
    genoa_jan = agg_df[(agg_df['port'] == 'Genoa') & (agg_df['date'].dt.month == 1)]
    assert len(genoa_jan) == 1
    # 10.0 + 5.0
    assert genoa_jan.iloc[0]['empty_out_teu'] == 15.0
    # 8.0 + 2.0
    assert genoa_jan.iloc[0]['empty_in_teu'] == 10.0
    
    # Naples has single row
    naples = agg_df[agg_df['port'] == 'Naples']
    assert len(naples) == 1
    assert naples.iloc[0]['empty_in_teu'] == 10.0

def test_signals_computation():
    agg_df = pd.DataFrame({
        'date': ['2018-01-31'],
        'port': ['Genoa'],
        'container_type': ['20ST'],
        'empty_out_teu': [15.0],
        'empty_in_teu': [10.0]
    })
    
    signals = compute_historical_signals(agg_df)
    
    assert list(signals.columns) == ['period', 'port', 'container_type', 'inferred_demand', 'inferred_supply']
    assert signals.iloc[0]['inferred_demand'] == 15.0
    assert signals.iloc[0]['inferred_supply'] == 10.0

def test_net_balance_and_classification():
    signals = pd.DataFrame({
        'period': ['2018-01-31', '2018-02-28', '2018-03-31'],
        'port': ['A', 'B', 'C'],
        'container_type': ['20', '20', '20'],
        'inferred_demand': [15.0, 10.0, 10.0], # out
        'inferred_supply': [5.0, 15.0, 10.0]   # in
    })
    
    # net_balance = supply - demand
    bal = compute_net_balance(signals)
    
    # A has shortage (-10)
    assert bal.iloc[0]['balance'] == -10.0
    assert bal.iloc[0]['is_shortage'] is True
    assert bal.iloc[0]['balance_status'] == 'shortage'
    
    # B has surplus (+5)
    assert bal.iloc[1]['balance'] == 5.0
    assert bal.iloc[1]['is_surplus'] is True
    assert bal.iloc[1]['balance_status'] == 'surplus'
    
    # C is balanced (0)
    assert bal.iloc[2]['balance'] == 0.0
    assert bal.iloc[2]['is_shortage'] is False
    assert bal.iloc[2]['is_surplus'] is False
    assert bal.iloc[2]['balance_status'] == 'balanced'

def test_priority_score():
    net_bal = pd.DataFrame({
        'balance': [-10.0, 5.0, 0.0]
    })
    
    # Priority is positive for shortages based on weight
    scored = compute_priority_score(net_bal, weight_factor=2.0)
    
    assert scored.iloc[0]['criticality_score'] == 20.0
    assert scored.iloc[1]['criticality_score'] == 0.0
    assert scored.iloc[2]['criticality_score'] == 0.0

def test_edge_cases():
    # Zeros
    empty_df = pd.DataFrame()
    assert aggregate_historical_data(empty_df).empty
    
    # Single port/type subsets
    single = pd.DataFrame({
        'date': ['2018-01-01'],
        'port': ['Unknown'],
        'container_type': ['Unk'],
        'empty_out_teu': [0.0],
        'empty_in_teu': [0.0],
        'full_in_teu': [0.0], 'full_out_teu': [0.0]
    })
    
    agg = aggregate_historical_data(single, freq='ME')
    sig = compute_historical_signals(agg)
    bal = compute_net_balance(sig)
    pri = compute_priority_score(bal)
    
    assert pri.iloc[0]['balance'] == 0.0
    assert pri.iloc[0]['is_shortage'] is False
    assert pri.iloc[0]['criticality_score'] == 0.0
