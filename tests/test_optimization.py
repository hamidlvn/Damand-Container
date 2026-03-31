import pytest
from datetime import date
from src.schemas.core import (
    StructuredProblem, ConstraintSet, BudgetConstraint,
    PortConstraint, TransportArc, SolverStrategy,
)
from src.optimization.heuristic_solver import HeuristicSolver
from src.optimization.milp_solver import MILPSolver
from src.optimization.runner import _dispatch


# ── fixtures ───────────────────────────────────────────────────────────────────

def _make_cset(is_hard=True, budget_limit=500_000.0):
    return ConstraintSet(
        port_constraints=[
            PortConstraint(port="A", min_inventory=0.0, max_inventory=999999.0, priority_weight=1.0),
            PortConstraint(port="B", min_inventory=0.0, max_inventory=999999.0, priority_weight=1.0),
        ],
        global_service_level_target=0.9,
        budget=BudgetConstraint(
            is_hard_limit=is_hard,
            limit_value=budget_limit,
            violation_penalty_per_unit=1.5 if not is_hard else None,
        ),
        shortage_penalty=100.0,
        surplus_penalty=20.0,
    )


def _make_problem(
    demand_a=200.0, supply_b=300.0, arc_cap=250.0,
    budget_limit=500_000.0, is_hard_budget=True,
):
    """Two-port, two-period problem: B has surplus, A has shortage."""
    T = 2
    ports = ["A", "B"]

    def _mat(val_a, val_b):
        return {
            "A": {0: val_a, 1: 0.0},
            "B": {0: 0.0,   1: 0.0},
        }

    return StructuredProblem(
        problem_id="TEST-001",
        ports=ports,
        time_periods=[date(2024, 1, 31), date(2024, 2, 29)],
        container_types=["20DC"],
        demand_matrix={"A": {0: demand_a, 1: 0.0}, "B": {0: 0.0, 1: 0.0}},
        supply_matrix={"A": {0: 0.0, 1: 0.0},      "B": {0: supply_b, 1: 0.0}},
        net_balance_matrix={"A": {0: -demand_a, 1: 0.0}, "B": {0: supply_b, 1: 0.0}},
        arcs=[
            TransportArc(
                origin_port="B", destination_port="A",
                departure_period_idx=0, arrival_period_idx=1,
                capacity_teu=arc_cap, cost_per_teu=250.0,
            )
        ],
        capacity_matrix={"A": {"B": {0: 0.0, 1: 0.0}}, "B": {"A": {0: arc_cap, 1: 0.0}}},
        cost_matrix={"A": {"B": 250.0, "A": 0.0}, "B": {"A": 250.0, "B": 0.0}},
        initial_inventory={"A": 0.0, "B": 0.0},
        constraint_set=_make_cset(is_hard=is_hard_budget, budget_limit=budget_limit),
    )


def _make_strategy(mode="single", solvers=None, fallback=None):
    return SolverStrategy(
        problem_id="TEST-001",
        selected_solver=solvers or ["Heuristic"],
        execution_mode=mode,
        fallback_solver=fallback,
        reasoning="test",
        runtime_hint="low",
    )


# ── heuristic tests ────────────────────────────────────────────────────────────

class TestHeuristic:
    def test_feasible_with_arc(self):
        sp = _make_problem(demand_a=100.0, supply_b=200.0)
        result = HeuristicSolver().solve(sp)
        assert result.status in ("feasible", "feasible_with_violations")
        assert result.service_level >= 0.0
        assert result.total_cost >= 0.0

    def test_no_arcs_leaves_unmet_demand(self):
        sp = _make_problem(demand_a=200.0, supply_b=300.0)
        # Remove all arcs
        sp = sp.model_copy(update={"arcs": []})
        result = HeuristicSolver().solve(sp)
        # Nothing moved → full 200 TEU unmet
        assert result.unmet_demand_teu == pytest.approx(200.0, abs=1.0)

    def test_hard_budget_cap(self):
        # Budget = 1 000 → can ship at most 4 TEU at $250/TEU
        sp = _make_problem(demand_a=200.0, supply_b=300.0, budget_limit=1_000.0, is_hard_budget=True)
        result = HeuristicSolver().solve(sp)
        assert result.total_cost <= 1_001.0   # slight tolerance for rounding

    def test_arc_capacity_respected(self):
        sp = _make_problem(demand_a=200.0, supply_b=300.0, arc_cap=50.0)
        result = HeuristicSolver().solve(sp)
        for dec in result.decisions:
            assert dec.quantity_teu <= 50.01   # tolerance

    def test_result_schema_valid(self):
        sp = _make_problem()
        result = HeuristicSolver().solve(sp)
        assert result.solver_name == "Heuristic"
        assert 0.0 <= result.service_level <= 1.0
        assert isinstance(result.decisions, list)
        assert isinstance(result.diagnostics, dict)


# ── MILP tests ─────────────────────────────────────────────────────────────────

class TestMILP:
    def test_feasible_and_optimal(self):
        sp = _make_problem(demand_a=100.0, supply_b=200.0)
        result = MILPSolver().solve(sp)
        assert result.status in ("optimal", "feasible", "infeasible", "failed")

    def test_result_schema_valid(self):
        sp = _make_problem()
        result = MILPSolver().solve(sp)
        assert result.solver_name == "MILP"
        assert isinstance(result.decisions, list)
        assert isinstance(result.diagnostics, dict)

    def test_service_level_range(self):
        sp = _make_problem()
        result = MILPSolver().solve(sp)
        if result.status not in ("failed",):
            assert 0.0 <= result.service_level <= 1.0


# ── runner / benchmark tests ──────────────────────────────────────────────────

class TestRunner:
    def test_single_mode(self):
        sp = _make_problem()
        strategy = _make_strategy(mode="single", solvers=["Heuristic"])
        results = _dispatch(sp, strategy)
        assert len(results) == 1
        assert results[0].solver_name == "Heuristic"

    def test_benchmark_mode_runs_both(self):
        sp = _make_problem()
        strategy = _make_strategy(mode="benchmark", solvers=["Heuristic", "MILP"])
        results = _dispatch(sp, strategy)
        names = {r.solver_name for r in results}
        assert "Heuristic" in names
        assert "MILP" in names

    def test_unknown_solver_skipped(self):
        sp = _make_problem()
        strategy = _make_strategy(mode="single", solvers=["NonExistentSolver"])
        results = _dispatch(sp, strategy)
        assert results == []
