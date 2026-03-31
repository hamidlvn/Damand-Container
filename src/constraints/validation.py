from src.schemas.core import ConstraintSet
import logging

logger = logging.getLogger(__name__)

class ConstraintValidationError(ValueError):
    """Exception raised for logically invalid or contradictory settings."""
    pass

def validate_constraint_set(cset: ConstraintSet):
    """
    Checks the defined constraints for contradictions or unsupported values
    which would otherwise crash mathematical solvers helplessly.
    """
    if cset.global_service_level_target < 0.0 or cset.global_service_level_target > 1.0:
        raise ConstraintValidationError("global_service_level_target must be percentage between 0.0 and 1.0")

    if cset.budget.limit_value < 0.0:
        raise ConstraintValidationError("budget limit_value cannot be negative")

    if not cset.budget.is_hard_limit and cset.budget.violation_penalty_per_unit is None:
        raise ConstraintValidationError("Soft budgets must have a defined violation penalty.")

    if cset.shortage_penalty < 0.0 or cset.surplus_penalty < 0.0:
        raise ConstraintValidationError("Penalties cannot be negative representations")

    for p in cset.port_constraints:
        if p.min_inventory < 0.0:
            raise ConstraintValidationError(f"min_inventory for port {p.port} cannot be negative.")
        
        if p.max_inventory < p.min_inventory:
            raise ConstraintValidationError(
                f"Contradiction: max_inventory ({p.max_inventory}) "
                f"is less than min_inventory ({p.min_inventory}) for port {p.port}."
            )
            
        if p.service_level_target is not None and (p.service_level_target < 0.0 or p.service_level_target > 1.0):
            raise ConstraintValidationError(f"Service level target override for port {p.port} must be 0-1.")
            
    logger.info("Constraints validation passed. Model is logically sound.")
    return True
