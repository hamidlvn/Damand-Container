import pytest
from src.schemas.core import PortConstraint, ConstraintSet, BudgetConstraint
from src.constraints.builder import ConstraintBuilder
from src.constraints.validation import validate_constraint_set, ConstraintValidationError

def test_builder_defaults():
    cfg = {
        "constraints": {
            "default_port_constraints": {
                "min_inventory": 50.0,
                "max_inventory": 1000.0,
                "priority_weight": 2.5
            },
            "global_service_level_target": 0.95,
            "budget": {
                "is_hard_limit": False,
                "limit_value": 50000.0,
                "violation_penalty_per_unit": 2.0
            },
            "shortage_penalty": 200.0,
            "surplus_penalty": 75.0
        }
    }
    
    builder = ConstraintBuilder(cfg)
    ports = {"PortA", "PortB"}
    
    p_constraints = builder.build_port_constraints(ports)
    assert len(p_constraints) == 2
    assert p_constraints[0].port in ports
    assert p_constraints[0].min_inventory == 50.0
    
    cset = builder.build_global_constraints(p_constraints)
    
    assert cset.global_service_level_target == 0.95
    assert cset.budget.limit_value == 50000.0
    assert cset.budget.is_hard_limit is False
    assert cset.budget.violation_penalty_per_unit == 2.0

def test_validation_logic():
    p_valid = PortConstraint(port="Valid", min_inventory=0.0, max_inventory=100.0, priority_weight=1.0)
    p_invalid = PortConstraint(port="Invalid", min_inventory=150.0, max_inventory=100.0, priority_weight=1.0)
    
    budget_valid = BudgetConstraint(is_hard_limit=True, limit_value=1000.0)
    budget_invalid_soft = BudgetConstraint(is_hard_limit=False, limit_value=100.0, violation_penalty_per_unit=None)
    
    cset = ConstraintSet(
        port_constraints=[p_valid, p_invalid],
        global_service_level_target=0.9,
        budget=budget_valid,
        shortage_penalty=1.0,
        surplus_penalty=1.0
    )
    
    with pytest.raises(ConstraintValidationError, match="Contradiction: max_inventory"):
        validate_constraint_set(cset)
        
    cset2 = ConstraintSet(
        port_constraints=[p_valid],
        global_service_level_target=0.9,
        budget=budget_invalid_soft,
        shortage_penalty=1.0,
        surplus_penalty=1.0
    )
    
    with pytest.raises(ConstraintValidationError, match="Soft budgets must have a defined violation penalty."):
        validate_constraint_set(cset2)
