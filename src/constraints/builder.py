from typing import List, Dict, Any, Set
from src.schemas.core import PortConstraint, ConstraintSet, BudgetConstraint
import logging

logger = logging.getLogger(__name__)

class ConstraintBuilder:
    """
    Constructs solver-ready Business Constraint formulations by merging 
    default planning assumptions with any specific overrides structurally.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("constraints", {})
        self.defaults = self.config.get("default_port_constraints", {})

    def build_port_constraints(self, unique_ports: Set[str]) -> List[PortConstraint]:
        """
        Builds a PortConstraint object for every required port.
        Applies system defaults if specific overrides don't exist in config.
        """
        default_min = float(self.defaults.get("min_inventory", 0.0))
        default_max = float(self.defaults.get("max_inventory", 999999.0))
        default_weight = float(self.defaults.get("priority_weight", 1.0))
        default_service_target = self.defaults.get("service_level_target", None)

        port_overrides = self.config.get("port_overrides", {})
        
        constraints = []
        for port in sorted(unique_ports):
            override = port_overrides.get(port, {})
            # Read service override explicitly, cast float if populated
            s_target = override.get("service_level_target", default_service_target)
            if s_target is not None:
                s_target = float(s_target)

            pc = PortConstraint(
                port=port,
                min_inventory=float(override.get("min_inventory", default_min)),
                max_inventory=float(override.get("max_inventory", default_max)),
                priority_weight=float(override.get("priority_weight", default_weight)),
                service_level_target=s_target
            )
            constraints.append(pc)
            
        return constraints

    def build_global_constraints(self, port_constraints: List[PortConstraint]) -> ConstraintSet:
        """
        Assembles the comprehensive ConstraintSet linking all local rules to 
        the unified global parameters including detailed Budget profiles.
        """
        budget_cfg = self.config.get("budget", {})
        
        budget = BudgetConstraint(
            is_hard_limit=bool(budget_cfg.get("is_hard_limit", True)),
            limit_value=float(budget_cfg.get("limit_value", 1000000.0)),
            violation_penalty_per_unit=budget_cfg.get("violation_penalty_per_unit", None)
        )
        
        # Cast optional violation penalty correctly if soft
        if not budget.is_hard_limit and budget.violation_penalty_per_unit is not None:
             budget.violation_penalty_per_unit = float(budget.violation_penalty_per_unit)

        return ConstraintSet(
            port_constraints=port_constraints,
            global_service_level_target=float(self.config.get("global_service_level_target", 0.90)),
            budget=budget,
            shortage_penalty=float(self.config.get("shortage_penalty", 100.0)),
            surplus_penalty=float(self.config.get("surplus_penalty", 50.0)),
            global_max_moves_teu=self.config.get("global_max_moves_teu", None)
        )
