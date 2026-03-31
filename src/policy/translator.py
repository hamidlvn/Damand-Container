"""
translator.py
=============
Converts raw AllocationDecision objects from a SolverResult into
human-facing PolicyAction objects with priority labels and rationales.

Priority assignment rules (transparent, documented):
──────────────────────────────────────────────────────
  HIGH   : quantity_teu ≥ HIGH_THRESHOLD (default 200 TEU)
  MEDIUM : quantity_teu ≥ MED_THRESHOLD  (default 50 TEU)
  LOW    : quantity_teu < MED_THRESHOLD

Priority is quantity-driven as a proxy for urgency: larger moves respond
to larger imbalances and therefore affect service level the most.
A future extension can weight by net_balance severity from StructuredProblem.
"""

from typing import List
from src.schemas.core import AllocationDecision, PolicyAction, SolverResult

HIGH_THRESHOLD = 200.0   # TEU – configurable
MED_THRESHOLD  = 50.0    # TEU – configurable


def _assign_priority(qty: float) -> str:
    if qty >= HIGH_THRESHOLD:
        return "High"
    elif qty >= MED_THRESHOLD:
        return "Medium"
    return "Low"


def _action_rationale(decision: AllocationDecision, priority: str) -> str:
    return (
        f"Move {decision.quantity_teu:.1f} TEU of {decision.container_type} "
        f"from {decision.origin_port} → {decision.destination_port} via {decision.mode} "
        f"(depart T={decision.departure_period_idx}, arrive T={decision.arrival_period_idx}). "
        f"Priority={priority}. Estimated cost: ${decision.cost:,.2f}."
    )


def translate_decisions(result: SolverResult) -> List[PolicyAction]:
    """
    Converts every AllocationDecision in a SolverResult into a PolicyAction.
    Returns an empty list if the solver failed or produced no decisions.
    """
    actions: List[PolicyAction] = []
    for idx, dec in enumerate(result.decisions):
        priority = _assign_priority(dec.quantity_teu)
        actions.append(PolicyAction(
            action_id=f"{result.solver_name}-{idx+1:04d}",
            action_type="reposition",
            origin_port=dec.origin_port,
            destination_port=dec.destination_port,
            mode=dec.mode,
            container_type=dec.container_type,
            quantity_teu=dec.quantity_teu,
            departure_period_idx=dec.departure_period_idx,
            arrival_period_idx=dec.arrival_period_idx,
            estimated_cost=dec.cost,
            priority_level=priority,
            rationale=_action_rationale(dec, priority),
        ))

    # Sort: High → Medium → Low, then by cost DESC within each tier
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(actions, key=lambda a: (priority_order[a.priority_level], -a.estimated_cost))
