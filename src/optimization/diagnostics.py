from typing import Dict, List, Tuple
from src.schemas.core import StructuredProblem, TransportArc


def compute_service_level(
    demand_matrix: Dict[str, Dict[int, float]],
    unmet: Dict[str, Dict[int, float]],
) -> float:
    """Service level = (total demand met) / (total demand)."""
    total_demand = sum(v for row in demand_matrix.values() for v in row.values())
    total_unmet = sum(v for row in unmet.values() for v in row.values())
    if total_demand == 0:
        return 1.0
    return max(0.0, 1.0 - total_unmet / total_demand)


def get_port_constraint(sp: StructuredProblem, port: str) -> Tuple[float, float, float]:
    """Returns (min_inventory, max_inventory, priority_weight) for a port."""
    port_map = {pc.port: pc for pc in sp.constraint_set.port_constraints}
    pc = port_map.get(port)
    if pc:
        return pc.min_inventory, pc.max_inventory, pc.priority_weight
    return 0.0, 999999.0, 1.0


def arcs_departing_at(sp: StructuredProblem, t: int) -> List[TransportArc]:
    return [a for a in sp.arcs if a.departure_period_idx == t]


def check_budget_feasibility(total_cost: float, sp: StructuredProblem) -> List[str]:
    """Returns a list of violated assumptions (empty if clean)."""
    warnings = []
    budget = sp.constraint_set.budget
    if budget.is_hard_limit and total_cost > budget.limit_value:
        warnings.append(
            f"Hard budget violated: cost={total_cost:.2f} > limit={budget.limit_value:.2f}"
        )
    return warnings
