import logging
from src.schemas.core import StructuredProblem

logger = logging.getLogger(__name__)

class ProblemValidationError(ValueError):
    """Exception raised for illogical indexing or structural misalignments in Problem Matrices."""
    pass

def validate_structured_problem(sp: StructuredProblem):
    """
    Checks the synthesized array formulations before pushing them into complex Mathematical Optimization Layers.
    Validations are structural bounds: matching Port configurations, aligned horizon matrix lengths.
    """
    if not sp.ports:
        raise ProblemValidationError("No active ports defined in Network.")
        
    if not sp.time_periods:
        raise ProblemValidationError("No discrete time periods projected across horizon.")
        
    for demand_dict in sp.demand_matrix.values():
        if len(demand_dict) != len(sp.time_periods):
             raise ProblemValidationError(f"Temporal dimension mismatch. Expected {len(sp.time_periods)} indexes per Port Matrix row.")
             
    for demand_dict in sp.demand_matrix.values():
        for t_idx, val in demand_dict.items():
            if val < 0.0:
                raise ProblemValidationError(f"Negative absolute demand value mapped natively: {val} at T={t_idx}")
                
    for arc in sp.arcs:
        if arc.origin_port not in sp.ports or arc.destination_port not in sp.ports:
            raise ProblemValidationError(f"Undefined graph edge. Unrecognized active port binding constraint: {arc.origin_port} -> {arc.destination_port}")
            
    # Check default constraint values are safe
    for pc in sp.constraint_set.port_constraints:
        if pc.port not in sp.ports:
            logger.warning(f"Business constraint provided for unregistered active graph port: {pc.port}")

    logger.info("Structured Problem formulation validation passed. Matrices logically secure for optimization.")
    return True
