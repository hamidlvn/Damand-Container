from dataclasses import dataclass
from typing import Dict, Any
from src.schemas.core import StructuredProblem

@dataclass
class ProblemFeatures:
    """
    Extracted size and complexity indicators from a StructuredProblem.
    These features drive the rule-based solver selection engine.
    """
    num_ports: int
    num_time_periods: int
    num_arcs: int
    num_container_types: int
    has_soft_budget: bool
    has_per_port_service_override: bool
    problem_size_score: int  # Composite score: ports * periods * arcs (scaled)


def extract_features(sp: StructuredProblem) -> ProblemFeatures:
    """
    Extracts scalar complexity indicators from a StructuredProblem object.
    No solver logic; purely a measurement step.
    """
    num_ports = len(sp.ports)
    num_periods = len(sp.time_periods)
    num_arcs = len(sp.arcs)
    num_ctypes = len(sp.container_types)

    # Soft budget: adds non-linearity to the problem
    has_soft_budget = not sp.constraint_set.budget.is_hard_limit

    # Per-port service overrides signal heterogeneous constraint density
    has_port_override = any(
        pc.service_level_target is not None
        for pc in sp.constraint_set.port_constraints
    )

    # Composite size: product of key cardinalities, square-root scaled
    import math
    size_score = math.isqrt(num_ports * num_periods * max(num_arcs, 1))

    return ProblemFeatures(
        num_ports=num_ports,
        num_time_periods=num_periods,
        num_arcs=num_arcs,
        num_container_types=num_ctypes,
        has_soft_budget=has_soft_budget,
        has_per_port_service_override=has_port_override,
        problem_size_score=size_score,
    )


class SelectionRules:
    """
    Deterministic rule-based engine that maps extracted ProblemFeatures to a SolverStrategy.

    Decision boundaries (configurable via pipeline.yaml):
      ┌──────────────────────────────────────────────────────────────────┐
      │ arcs ≤ small_arcs AND periods ≤ small_time  →  MILP (single)   │
      │ arcs ≥ large_arcs OR  periods ≥ large_time  →  Heuristic        │
      │ otherwise                                   →  Benchmark (both) │
      └──────────────────────────────────────────────────────────────────┘
    Soft-budget and per-port overrides shift the boundary one tier upward.
    """

    def __init__(self, limits: Dict[str, Any]):
        self.small_arcs = int(limits.get("small_problem_arcs_max", 50))
        self.small_time = int(limits.get("small_problem_time_max", 3))
        self.large_arcs = int(limits.get("large_problem_arcs_min", 500))
        self.large_time = int(limits.get("large_problem_time_min", 12))

    def select(self, features: ProblemFeatures) -> Dict[str, Any]:
        """
        Returns a dict of raw strategy fields.
        Called by service.py which assembles the final SolverStrategy object.
        """
        arcs = features.num_arcs
        periods = features.num_time_periods
        complexity_boost = features.has_soft_budget or features.has_per_port_service_override

        # Adjust thresholds downward when constraints are more complex
        effective_small_arcs = self.small_arcs if not complexity_boost else self.small_arcs // 2
        effective_small_time = self.small_time if not complexity_boost else max(self.small_time - 1, 1)

        # --- Rule evaluation (deterministic, in priority order) ---
        if arcs >= self.large_arcs or periods >= self.large_time:
            solver = ["Heuristic"]
            mode = "single"
            fallback = "MILP"
            hint = "high"
            reason = (
                f"Problem is LARGE (arcs={arcs}, periods={periods}). "
                "MILP may be computationally intractable at this scale; "
                "Heuristic is selected as primary with MILP as fallback on smaller sub-problems."
            )

        elif arcs <= effective_small_arcs and periods <= effective_small_time:
            solver = ["MILP"]
            mode = "single"
            fallback = "Heuristic"
            hint = "low"
            reason = (
                f"Problem is SMALL (arcs={arcs}, periods={periods}). "
                "MILP can find the provably optimal solution within practical runtimes."
            )
            if complexity_boost:
                reason += " Note: soft-budget/per-port override detected; fallback Heuristic is available."

        else:
            solver = ["MILP", "Heuristic"]
            mode = "benchmark"
            fallback = None
            hint = "medium"
            reason = (
                f"Problem is MEDIUM complexity (arcs={arcs}, periods={periods}). "
                "Both MILP and Heuristic will run in benchmark mode so their "
                "cost, feasibility, and runtime can be compared empirically."
            )
            if complexity_boost:
                reason += " Soft constraints/per-port overrides detected, increasing solution space."

        return {
            "selected_solver": solver,
            "execution_mode": mode,
            "fallback_solver": fallback,
            "reasoning": reason,
            "runtime_hint": hint,
        }
