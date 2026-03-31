"""
Heuristic Solver
================
Algorithm (deterministic, greedy, period-by-period):

For each time period t (in chronological order):
  1. Compute available supply at each port  = supply[p,t] + inventory[p]
  2. Compute net shortage at each port      = demand[p,t] - available_supply[p,t]
  3. Build shortage list (sorted by severity × priority_weight DESC)
  4. Build surplus list  (sorted by surplus volume DESC)
  5. For each shortage port (highest first):
       For each feasible arc departing at t toward the shortage port:
         Allocate min(arc_capacity, surplus_available, shortage_remaining)
         Deduct from surplus origin, deduct from shortage, accumulate cost
         Stop when shortage is met or no feasible arcs remain
  6. Update inventories post-allocation

Objective approximated: total transport cost + shortage_penalty × unmet + surplus_penalty × leftover
"""

import time
from copy import deepcopy
from typing import Dict, List

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


class HeuristicSolver(BaseSolver):

    @property
    def name(self) -> str:
        return "Heuristic"

    def solve(self, problem: StructuredProblem) -> SolverResult:
        t_start = time.time()
        sp = problem
        cs = sp.constraint_set
        T = len(sp.time_periods)

        # ── mutable state ────────────────────────────────────────────────────
        # inventory[port] tracks rolling ending stock (starts at initial)
        inventory: Dict[str, float] = {p: sp.initial_inventory.get(p, 0.0) for p in sp.ports}
        # remaining arc capacity (per arc index)
        arc_cap: Dict[int, float] = {i: a.capacity_teu for i, a in enumerate(sp.arcs)}
        # unmet demand tracker [port][t]
        unmet: Dict[str, Dict[int, float]] = {
            p: {t: 0.0 for t in range(T)} for p in sp.ports
        }

        decisions: List[AllocationDecision] = []
        total_cost = 0.0

        # ── default container type (aggregate across types for simplicity) ───
        ctype = sp.container_types[0] if sp.container_types else "UNKNOWN"

        for t in range(T):
            # --- available supply at each port this period ---
            avail: Dict[str, float] = {}
            for p in sp.ports:
                _, max_inv, _ = get_port_constraint(sp, p)
                avail[p] = min(
                    sp.supply_matrix[p].get(t, 0.0) + inventory[p],
                    max_inv,
                )

            # --- shortage & surplus this period ---
            shortage: Dict[str, float] = {}
            surplus: Dict[str, float] = {}

            for p in sp.ports:
                demand_pt = sp.demand_matrix[p].get(t, 0.0)
                min_inv, _, pw = get_port_constraint(sp, p)
                net = avail[p] - demand_pt
                if net < 0:
                    shortage[p] = abs(net) * pw   # weight by priority
                else:
                    surplus[p] = max(0.0, net - min_inv)

            # Sort: most severe shortage first, most surplus first
            shortage_sorted = sorted(shortage.items(), key=lambda x: x[1], reverse=True)
            surplus_sorted  = sorted(surplus.items(),  key=lambda x: x[1], reverse=True)

            if not shortage_sorted or not surplus_sorted:
                # Nothing to do this period
                for p in sp.ports:
                    demand_pt = sp.demand_matrix[p].get(t, 0.0)
                    unmet[p][t] = max(0.0, demand_pt - avail[p])
                self._update_inventories(inventory, sp, t, avail, decisions)
                continue

            # --- feasible arcs departing at period t ---
            arcs_at_t = [
                (i, a) for i, a in enumerate(sp.arcs)
                if a.departure_period_idx == t
            ]

            # Build lookup: destination → list of (arc_idx, arc)
            dest_arcs: Dict[str, list] = {}
            for i, a in arcs_at_t:
                dest_arcs.setdefault(a.destination_port, []).append((i, a))

            for sht_port, sht_weight in shortage_sorted:
                remaining_shortage = shortage.get(sht_port, 0.0) / max(
                    get_port_constraint(sp, sht_port)[2], 1.0
                )   # un-weight to get TEU

                feasible_arcs = dest_arcs.get(sht_port, [])
                if not feasible_arcs:
                    continue
                    
                # Sort arcs by cost to naturally prioritize cheaper modes (Sea -> Rail -> Road)
                feasible_arcs = sorted(feasible_arcs, key=lambda item: item[1].cost_per_teu)

                for srv_port, srv_vol in surplus_sorted:
                    if remaining_shortage <= 0:
                        break
                    if srv_vol <= 0:
                        continue

                    for arc_idx, arc in feasible_arcs:
                        if arc.origin_port != srv_port:
                            continue
                        if arc_cap[arc_idx] <= 0:
                            continue

                        qty = min(
                            remaining_shortage,
                            arc_cap[arc_idx],
                            surplus.get(srv_port, 0.0),
                        )
                        if qty <= 0:
                            continue

                        move_cost = qty * arc.cost_per_teu

                        # Hard budget check per move
                        if cs.budget.is_hard_limit and (total_cost + move_cost) > cs.budget.limit_value:
                            qty = (cs.budget.limit_value - total_cost) / arc.cost_per_teu
                            qty = max(0.0, qty)
                            if qty <= 0:
                                break
                            move_cost = qty * arc.cost_per_teu

                        # Commit the allocation
                        decisions.append(AllocationDecision(
                            origin_port=arc.origin_port,
                            destination_port=arc.destination_port,
                            mode=arc.mode,
                            container_type=ctype,
                            quantity_teu=round(qty, 2),
                            departure_period_idx=arc.departure_period_idx,
                            arrival_period_idx=arc.arrival_period_idx,
                            cost=round(move_cost, 2),
                        ))

                        total_cost += move_cost
                        arc_cap[arc_idx] -= qty
                        surplus[srv_port] = max(0.0, surplus.get(srv_port, 0.0) - qty)
                        remaining_shortage -= qty

            # Record unmet demand for this period
            for p in sp.ports:
                demand_pt = sp.demand_matrix[p].get(t, 0.0)
                served = avail[p] - max(0.0, avail[p] - demand_pt)
                unmet[p][t] = max(0.0, demand_pt - served)

            self._update_inventories(inventory, sp, t, avail, decisions)

        # ── summary metrics ──────────────────────────────────────────────────
        total_unmet = sum(v for row in unmet.values() for v in row.values())
        total_surplus_remaining = sum(
            max(0.0, inventory.get(p, 0.0)) for p in sp.ports
        )
        svc_level = compute_service_level(sp.demand_matrix, unmet)

        pen = cs.shortage_penalty * total_unmet + cs.surplus_penalty * total_surplus_remaining
        if not cs.budget.is_hard_limit and total_cost > cs.budget.limit_value:
            pen += cs.budget.violation_penalty_per_unit * (total_cost - cs.budget.limit_value)
        obj = total_cost + pen

        budget_warnings = check_budget_feasibility(total_cost, sp)
        status = "feasible" if not budget_warnings else "feasible_with_violations"

        return SolverResult(
            problem_id=sp.problem_id,
            solver_name=self.name,
            status=status,
            objective_value=round(obj, 2),
            total_cost=round(total_cost, 2),
            service_level=round(svc_level, 4),
            unmet_demand_teu=round(total_unmet, 2),
            surplus_remaining_teu=round(total_surplus_remaining, 2),
            solve_time_seconds=round(time.time() - t_start, 4),
            decisions=decisions,
            diagnostics={
                "budget_violations": budget_warnings,
                "periods_solved": T,
                "total_moves": len(decisions),
            },
        )

    @staticmethod
    def _update_inventories(
        inventory: Dict[str, float],
        sp: StructuredProblem,
        t: int,
        avail: Dict[str, float],
        decisions: List[AllocationDecision],
    ):
        """Roll inventory forward: consume demand, credit incoming arrivals."""
        for p in sp.ports:
            demand_pt = sp.demand_matrix[p].get(t, 0.0)
            min_inv, max_inv, _ = get_port_constraint(sp, p)
            inventory[p] = max(min_inv, avail[p] - demand_pt)
            inventory[p] = min(inventory[p], max_inv)

        # Credit containers that arrive at period t+1
        for dec in decisions:
            if dec.arrival_period_idx == t + 1:
                inventory[dec.destination_port] = min(
                    inventory.get(dec.destination_port, 0.0) + dec.quantity_teu,
                    get_port_constraint(sp, dec.destination_port)[1],
                )
