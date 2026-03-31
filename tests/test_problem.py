import pytest
import pandas as pd
from datetime import date
from src.schemas.core import ConstraintSet, CapacityContext, VoyageLeg, BudgetConstraint, PortConstraint
from src.problem.builder import ProblemBuilder
from src.problem.validation import validate_structured_problem, ProblemValidationError

def test_builder_indexing():
    # Construct mock data artifacts
    df = pd.DataFrame({
        'port': ['A', 'A', 'B', 'B'],
        'container_type': ['20DC', '20DC', '20DC', '20DC'],
        'target_period': [date(2018, 1, 31), date(2018, 2, 28), date(2018, 1, 31), date(2018, 2, 28)],
        'forecast_type': ['demand', 'demand', 'supply', 'supply'],
        'point_estimate': [100.0, 150.0, 50.0, 75.0]
    })
    
    b_constraint = BudgetConstraint(is_hard_limit=True, limit_value=1000.0)
    p_constraint = PortConstraint(port="A", min_inventory=0.0, max_inventory=1000.0, priority_weight=1.0)
    
    cset = ConstraintSet(
        port_constraints=[p_constraint],
        global_service_level_target=0.9,
        budget=b_constraint,
        shortage_penalty=10.0,
        surplus_penalty=5.0
    )
    
    v_leg = VoyageLeg(
        origin_port="A", destination_port="B",
        departure_time=date(2018, 1, 31), arrival_time=date(2018, 2, 28),
        capacity_teu=500.0, transit_time_periods=1, cost_per_teu=100.0
    )
    
    cctx = CapacityContext(voyage_legs=[v_leg])
    
    builder = ProblemBuilder(df, cset, cctx)
    probs = builder.build_problem("TEST-123")
    
    # Assert Time logic indexed correctly
    assert len(probs.time_periods) == 2
    assert probs.time_periods[0] == date(2018, 1, 31)
    
    # Assert Arcs mapping accurately matched physical times to solver indices
    assert len(probs.arcs) == 1
    arc = probs.arcs[0]
    assert arc.origin_port == "A"
    assert arc.destination_port == "B"
    assert arc.departure_period_idx == 0
    assert arc.arrival_period_idx == 1
    assert arc.capacity_teu == 500.0
    
    # Assert Matrix alignment successfully formed
    assert probs.demand_matrix["A"][0] == 100.0
    assert probs.demand_matrix["A"][1] == 150.0
    assert probs.supply_matrix["B"][0] == 50.0
    
    # Validation passes linearly
    assert validate_structured_problem(probs)

def test_validation_traps():
    # ... mock structural dependencies 
    from src.problem.models import StructuredProblem, TransportArc
    
    # Missing ports
    invalid_prob = StructuredProblem(
        problem_id="TEST-FAIL",
        ports=[], # Empty
        time_periods=[date(2018,1,1)],
        container_types=["20DC"],
        demand_matrix={},
        supply_matrix={},
        net_balance_matrix={},
        arcs=[],
        capacity_matrix={},
        cost_matrix={},
        initial_inventory={},
        constraint_set=ConstraintSet(
            port_constraints=[],
            global_service_level_target=0.9,
            budget=BudgetConstraint(is_hard_limit=True, limit_value=1000.0),
            shortage_penalty=1.0, surplus_penalty=1.0
        )
    )
    
    with pytest.raises(ProblemValidationError, match="No active ports defined"):
        validate_structured_problem(invalid_prob)
