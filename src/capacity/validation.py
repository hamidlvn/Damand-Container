from src.capacity.models import CapacityContext
import logging

logger = logging.getLogger(__name__)

class CapacityValidationError(ValueError):
    """Exception raised for illogical Transport properties (like negative costs)."""
    pass

def validate_capacity_context(ctx: CapacityContext):
    """
    Checks the physical transport limits verifying logic (no negative times/costs).
    Guarantees optimization models won't run into unbounded negative loops.
    """
    if ctx.global_teu_capacity_limit is not None and ctx.global_teu_capacity_limit < 0.0:
        raise CapacityValidationError("Global TEU capacity limit cannot be negatively bounded.")
        
    for l in ctx.voyage_legs:
        if l.origin_port == l.destination_port:
             raise CapacityValidationError(f"Self-loop detected: {l.origin_port} -> {l.destination_port}")

        if l.capacity_teu <= 0.0:
             raise CapacityValidationError(f"Invalid bounding strictly bounded: Capacity <= 0 on voyage: {l.origin_port} -> {l.destination_port}")
            
        if l.transit_time_periods <= 0:
             raise CapacityValidationError(f"Negative or zero time travel on voyage constraint: {l.origin_port} -> {l.destination_port}")
            
        if l.cost_per_teu < 0.0:
             raise CapacityValidationError(f"Negative transportation cost (infinite profit loop hazard): {l.origin_port} -> {l.destination_port}")
            
        if l.arrival_time <= l.departure_time:
             raise CapacityValidationError(f"Paradox hazard: Voyage arrives before it departs from {l.origin_port}")

    logger.info(f"Capacity network validation passed. Verified {len(ctx.voyage_legs)} voyages securely.")
    return True
