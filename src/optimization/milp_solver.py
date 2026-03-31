"""
MILP Solver (PuLP)
==================
Formulation summary:

Sets:
  P   – ports
  T   – time periods (0 … |T|-1)
  A   – transport arcs (from, to, dep_t, arr_t, cap, cost)

Decision variables:
  x[a]  ≥ 0  – TEU shipped on arc a          (continuous)
  u[p,t] ≥ 0  – unmet demand at (p, t)         (slack, continuous)
  s[p,t] ≥ 0  – surplus inventory at (p, t)    (slack, continuous)

Objective (minimise):
  Σ_a  cost_per_teu[a] * x[a]
  + shortage_penalty  * Σ_{p,t} u[p,t]
  + surplus_penalty   * Σ_{p,t} s[p,t]
  + (soft-budget penalty if applicable)

Constraints:
  [CAP]  x[a] ≤ capacity_teu[a]                     ∀ a
  [INV]  inv[p,t] = inv[p,t-1]
         + supply[p,t]
         + Σ_{a: arr=t, dest=p} x[a]
         - demand[p,t]
         - Σ_{a: dep=t, orig=p} x[a]
         + u[p,t] - s[p,t]                           ∀ p, t
  [INV_LB]  inv[p,t] ≥ min_inventory[p]              ∀ p, t
  [INV_UB]  inv[p,t] ≤ max_inventory[p]              ∀ p, t
  [BUDGET_HARD]  Σ_a cost_per_teu[a]*x[a] ≤ budget   (if hard)
"""

import time
from typing import Dict, List

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False

from src.optimization.base import BaseSolver
from src.optimization.diagnostics import (
    compute_service_level,
    get_port_constraint,
    check_budget_feasibility,
)
from src.schemas.core import (
    AllocationDecision,
    SolverResult,
    StructuredProblem,
)


class MILPSolver(BaseSolver):

    @property
    def name(self) -> str:
        return "MILP"

    def solve(self, problem: StructuredProblem) -> SolverResult:
        t_start = time.time()

        if not PULP_AVAILABLE:
            return self._failed(problem, "PuLP is not installed. Run: pip install pulp", t_start)

        sp = problem
        cs = sp.constraint_set
        P = sp.ports
        T = len(sp.time_periods)
        A = sp.arcs

        # ── Build model ──────────────────────────────────────────────────────
        model = pulp.LpProblem("EmptyContainer_Repositioning", pulp.LpMinimize)

        # Decision variables
        x = {i: pulp.LpVariable(f"x_{i}", lowBound=0) for i in range(len(A))}
        u = {(p, t): pulp.LpVariable(f"u_{p}_{t}", lowBound=0) for p in P for t in range(T)}
        s = {(p, t): pulp.LpVariable(f"s_{p}_{t}", lowBound=0) for p in P for t in range(T)}
        inv = {(p, t): pulp.LpVariable(f"inv_{p}_{t}", lowBound=0) for p in P for t in range(T)}

        # ── Objective ────────────────────────────────────────────────────────
        transport_cost = pulp.lpSum(A[i].cost_per_teu * x[i] for i in range(len(A)))
        unmet_penalty  = cs.shortage_penalty * pulp.lpSum(u[p, t] for p in P for t in range(T))
        surp_penalty   = cs.surplus_penalty  * pulp.lpSum(s[p, t] for p in P for t in range(T))

        obj = transport_cost + unmet_penalty + surp_penalty

        # Soft budget penalty
        if not cs.budget.is_hard_limit and cs.budget.violation_penalty_per_unit:
            over_budget = pulp.LpVariable("over_budget", lowBound=0)
            model += (transport_cost - over_budget <= cs.budget.limit_value, "SoftBudget_LB")
            obj = obj + cs.budget.violation_penalty_per_unit * over_budget

        model += obj

        # ── Constraints ──────────────────────────────────────────────────────
        # [CAP] arc capacity
        for i, arc in enumerate(A):
            model += (x[i] <= arc.capacity_teu, f"CAP_{i}")

        # [INV] inventory balance
        for p in P:
            min_inv, max_inv, _ = get_port_constraint(sp, p)
            for t in range(T):
                inflow_arcs  = pulp.lpSum(x[i] for i, a in enumerate(A) if a.destination_port == p and a.arrival_period_idx == t)
                outflow_arcs = pulp.lpSum(x[i] for i, a in enumerate(A) if a.origin_port == p and a.departure_period_idx == t)
                supply_pt    = sp.supply_matrix[p].get(t, 0.0)
                demand_pt    = sp.demand_matrix[p].get(t, 0.0)
                inv_prev     = sp.initial_inventory.get(p, 0.0) if t == 0 else inv[p, t - 1]

                model += (
                    inv[p, t] == inv_prev + supply_pt + inflow_arcs - demand_pt - outflow_arcs + u[p, t] - s[p, t],
                    f"INV_BAL_{p}_{t}",
                )
                model += (inv[p, t] >= min_inv, f"INV_LB_{p}_{t}")
                model += (inv[p, t] <= max_inv, f"INV_UB_{p}_{t}")

        # [BUDGET HARD]
        if cs.budget.is_hard_limit:
            model += (transport_cost <= cs.budget.limit_value, "BudgetHard")

        # [GLOBAL MAX TEU]
        if cs.global_max_moves_teu is not None:
            model += (pulp.lpSum(x[i] for i in range(len(A))) <= cs.global_max_moves_teu, "GlobalMaxTEU")

        # ── Solve ────────────────────────────────────────────────────────────
        solver = pulp.PULP_CBC_CMD(msg=0)
        model.solve(solver)

        elapsed = round(time.time() - t_start, 4)
        status_map = {
            pulp.LpStatusOptimal:    "optimal",
            pulp.LpStatusNotSolved:  "infeasible",
            pulp.LpStatusInfeasible: "infeasible",
            pulp.LpStatusUnbounded:  "failed",
            pulp.LpStatusUndefined:  "failed",
        }
        status = status_map.get(model.status, "failed")

        if status in ("infeasible", "failed"):
            return SolverResult(
                problem_id=sp.problem_id,
                solver_name=self.name,
                status=status,
                objective_value=0.0,
                total_cost=0.0,
                service_level=0.0,
                unmet_demand_teu=0.0,
                surplus_remaining_teu=0.0,
                solve_time_seconds=elapsed,
                decisions=[],
                diagnostics={"pulp_status": pulp.LpStatus[model.status]},
            )

        # ── Extract decisions ────────────────────────────────────────────────
        ctype = sp.container_types[0] if sp.container_types else "UNKNOWN"
        decisions: List[AllocationDecision] = []
        total_cost_val = 0.0

        for i, arc in enumerate(A):
            qty = pulp.value(x[i]) or 0.0
            if qty > 1e-4:
                cost_val = round(qty * arc.cost_per_teu, 2)
                total_cost_val += cost_val
                decisions.append(AllocationDecision(
                    origin_port=arc.origin_port,
                    destination_port=arc.destination_port,
                    mode=arc.mode,
                    container_type=ctype,
                    quantity_teu=round(qty, 2),
                    departure_period_idx=arc.departure_period_idx,
                    arrival_period_idx=arc.arrival_period_idx,
                    cost=cost_val,
                ))

        # ── KPIs ─────────────────────────────────────────────────────────────
        unmet_matrix = {
            p: {t: max(0.0, pulp.value(u[p, t]) or 0.0) for t in range(T)}
            for p in P
        }
        surp_matrix = {
            p: {t: max(0.0, pulp.value(s[p, t]) or 0.0) for t in range(T)}
            for p in P
        }

        total_unmet   = sum(v for row in unmet_matrix.values() for v in row.values())
        total_surplus  = sum(v for row in surp_matrix.values() for v in row.values())
        svc_level = compute_service_level(sp.demand_matrix, unmet_matrix)
        obj_val   = pulp.value(model.objective) or 0.0

        return SolverResult(
            problem_id=sp.problem_id,
            solver_name=self.name,
            status=status,
            objective_value=round(obj_val, 2),
            total_cost=round(total_cost_val, 2),
            service_level=round(svc_level, 4),
            unmet_demand_teu=round(total_unmet, 2),
            surplus_remaining_teu=round(total_surplus, 2),
            solve_time_seconds=elapsed,
            decisions=decisions,
            diagnostics={
                "pulp_status": pulp.LpStatus[model.status],
                "num_variables": model.numVariables(),
                "num_constraints": model.numConstraints(),
                "budget_violations": check_budget_feasibility(total_cost_val, sp),
            },
        )

    @staticmethod
    def _failed(sp: StructuredProblem, reason: str, t_start: float) -> SolverResult:
        return SolverResult(
            problem_id=sp.problem_id,
            solver_name="MILP",
            status="failed",
            objective_value=0.0,
            total_cost=0.0,
            service_level=0.0,
            unmet_demand_teu=0.0,
            surplus_remaining_teu=0.0,
            solve_time_seconds=round(time.time() - t_start, 4),
            decisions=[],
            diagnostics={"reason": reason},
        )
