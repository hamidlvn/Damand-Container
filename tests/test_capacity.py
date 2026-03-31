import pytest
import datetime
from src.schemas.core import VoyageLeg, CapacityContext
from src.capacity.generator import VoyageGenerator
from src.capacity.validation import validate_capacity_context, CapacityValidationError

def test_generator_synthetic_defaults():
    cfg = {
        "capacity": {
            "default_min_teu_capacity": 40.0,
            "default_max_teu_capacity": 500.0,
            "default_min_transit_time_periods": 1,
            "default_max_transit_time_periods": 2,
            "default_cost_per_teu": 300.0,
            "global_teu_capacity_limit": 10000.0
        }
    }
    
    generator = VoyageGenerator(cfg)
    ports = {"A", "B"}
    d1 = datetime.date(2018, 1, 31)
    periods = [d1]
    
    legs = generator.generate_voyage_legs(ports, periods)
    
    # 2 ports over 1 period = 2 legs (A->B, B->A).
    assert len(legs) == 2
    r_ab = [r for r in legs if r.origin_port == "A" and r.destination_port == "B"][0]
    
    # Cap should be randomized but bounded within specified configs
    assert 40.0 <= r_ab.capacity_teu <= 500.0
    assert 1 <= r_ab.transit_time_periods <= 2
    assert r_ab.cost_per_teu == 300.0
    assert r_ab.departure_time == d1
    assert r_ab.arrival_time > d1
    
    ctx = generator.build_context(legs)
    assert ctx.global_teu_capacity_limit == 10000.0

def test_validation_logic():
    # Construct a deliberately invalid paradox logic
    r_valid = VoyageLeg(
        origin_port="A", destination_port="B", departure_time=datetime.date(2018, 1, 31),
        arrival_time=datetime.date(2018, 2, 28), capacity_teu=100.0, transit_time_periods=1, cost_per_teu=100.0
    )
    
    # Trap Self-Loops
    r_self = VoyageLeg(
        origin_port="A", destination_port="A", departure_time=datetime.date(2018, 1, 31),
        arrival_time=datetime.date(2018, 2, 28), capacity_teu=100.0, transit_time_periods=1, cost_per_teu=100.0
    )
    
    ctx_invalid = CapacityContext(voyage_legs=[r_self])
    with pytest.raises(CapacityValidationError, match="Self-loop detected"):
        validate_capacity_context(ctx_invalid)
        
    # Trap Time Paradox (Arrives same day as Departure)
    r_paradox = VoyageLeg(
        origin_port="A", destination_port="B", departure_time=datetime.date(2018, 1, 31),
        arrival_time=datetime.date(2018, 1, 31), capacity_teu=100.0, transit_time_periods=0, cost_per_teu=100.0
    )
    
    ctx_invalid_time = CapacityContext(voyage_legs=[r_paradox])
    with pytest.raises(CapacityValidationError, match="Negative or zero time travel"):
        validate_capacity_context(ctx_invalid_time)
        
    # Valid
    ctx_valid = CapacityContext(voyage_legs=[r_valid])
    assert validate_capacity_context(ctx_valid) is True
