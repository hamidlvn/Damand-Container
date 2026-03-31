import pytest
from datetime import date
from src.schemas.core import (
    StructuredProblem, ConstraintSet, BudgetConstraint,
    PortConstraint, TransportArc, VoyageLeg,
)
from src.solver_selection.rules import extract_features, SelectionRules, ProblemFeatures

# ── helpers ───────────────────────────────────────────────────────────────────

LIMITS_DEFAULT = {
    "small_problem_arcs_max": 50,
    "small_problem_time_max": 3,
    "large_problem_arcs_min": 500,
    "large_problem_time_min": 12,
}


def _make_cset(is_hard_limit: bool = True, port_override: bool = False):
    pc = PortConstraint(
        port="A",
        min_inventory=0.0,
        max_inventory=1000.0,
        priority_weight=1.0,
        service_level_target=0.95 if port_override else None,
    )
    budget = BudgetConstraint(
        is_hard_limit=is_hard_limit,
        limit_value=500_000.0,
        violation_penalty_per_unit=1.5 if not is_hard_limit else None,
    )
    return ConstraintSet(
        port_constraints=[pc],
        global_service_level_target=0.9,
        budget=budget,
        shortage_penalty=100.0,
        surplus_penalty=50.0,
    )


def _make_problem(num_arcs: int, num_periods: int, is_hard_limit=True, port_override=False):
    ports = ["A", "B"]
    periods = [date(2024, i + 1, 28) for i in range(num_periods)]

    arcs = [
        TransportArc(
            origin_port="A", destination_port="B",
            departure_period_idx=0, arrival_period_idx=1,
            capacity_teu=200.0, cost_per_teu=250.0,
        )
        for _ in range(num_arcs)
    ]

    def _empty_mat(fill=0.0):
        return {p: {t: fill for t in range(num_periods)} for p in ports}

    return StructuredProblem(
        problem_id="TEST",
        ports=ports,
        time_periods=periods,
        container_types=["20DC"],
        demand_matrix=_empty_mat(),
        supply_matrix=_empty_mat(),
        net_balance_matrix=_empty_mat(),
        arcs=arcs,
        capacity_matrix={p: {q: {t: 200.0 for t in range(num_periods)} for q in ports} for p in ports},
        cost_matrix={p: {q: 250.0 for q in ports} for p in ports},
        initial_inventory={p: 0.0 for p in ports},
        constraint_set=_make_cset(is_hard_limit=is_hard_limit, port_override=port_override),
    )


# ── tests ─────────────────────────────────────────────────────────────────────

class TestFeatureExtraction:
    def test_basic_counts(self):
        sp = _make_problem(num_arcs=10, num_periods=2)
        f = extract_features(sp)
        assert f.num_ports == 2
        assert f.num_time_periods == 2
        assert f.num_arcs == 10
        assert f.has_soft_budget is False
        assert f.has_per_port_service_override is False

    def test_soft_budget_detected(self):
        sp = _make_problem(num_arcs=10, num_periods=2, is_hard_limit=False)
        f = extract_features(sp)
        assert f.has_soft_budget is True

    def test_per_port_override_detected(self):
        sp = _make_problem(num_arcs=10, num_periods=2, port_override=True)
        f = extract_features(sp)
        assert f.has_per_port_service_override is True


class TestSelectionRules:
    def test_small_problem_selects_milp(self):
        sp = _make_problem(num_arcs=10, num_periods=2)
        features = extract_features(sp)
        decision = SelectionRules(LIMITS_DEFAULT).select(features)

        assert decision["selected_solver"] == ["MILP"]
        assert decision["execution_mode"] == "single"
        assert decision["runtime_hint"] == "low"
        assert decision["fallback_solver"] == "Heuristic"

    def test_large_problem_selects_heuristic(self):
        sp = _make_problem(num_arcs=600, num_periods=15)
        features = extract_features(sp)
        decision = SelectionRules(LIMITS_DEFAULT).select(features)

        assert decision["selected_solver"] == ["Heuristic"]
        assert decision["execution_mode"] == "single"
        assert decision["runtime_hint"] == "high"
        assert decision["fallback_solver"] == "MILP"

    def test_medium_problem_selects_benchmark(self):
        sp = _make_problem(num_arcs=100, num_periods=6)
        features = extract_features(sp)
        decision = SelectionRules(LIMITS_DEFAULT).select(features)

        assert "MILP" in decision["selected_solver"]
        assert "Heuristic" in decision["selected_solver"]
        assert decision["execution_mode"] == "benchmark"
        assert decision["runtime_hint"] == "medium"

    def test_complexity_boost_shifts_boundary(self):
        # 30 arcs / 3 periods would normally → MILP (small)
        # but soft budget should shift threshold down → benchmark
        sp = _make_problem(num_arcs=30, num_periods=3, is_hard_limit=False)
        features = extract_features(sp)
        decision = SelectionRules(LIMITS_DEFAULT).select(features)

        # effective_small_arcs becomes 25, so 30 > 25 → medium
        assert decision["execution_mode"] == "benchmark"

    def test_reasoning_is_non_empty(self):
        for arcs, periods in [(5, 2), (100, 6), (600, 15)]:
            sp = _make_problem(arcs, periods)
            features = extract_features(sp)
            d = SelectionRules(LIMITS_DEFAULT).select(features)
            assert len(d["reasoning"]) > 20


class TestEdgeCases:
    def test_zero_arcs_stays_small(self):
        sp = _make_problem(num_arcs=0, num_periods=2)
        features = extract_features(sp)
        decision = SelectionRules(LIMITS_DEFAULT).select(features)
        assert decision["selected_solver"] == ["MILP"]

    def test_custom_limits_override(self):
        custom_limits = {
            "small_problem_arcs_max": 5,
            "small_problem_time_max": 1,
            "large_problem_arcs_min": 20,
            "large_problem_time_min": 5,
        }
        # 10 arcs / 3 periods → between 5 and 20 → benchmark with custom limits
        sp = _make_problem(num_arcs=10, num_periods=3)
        features = extract_features(sp)
        decision = SelectionRules(custom_limits).select(features)
        assert decision["execution_mode"] == "benchmark"
