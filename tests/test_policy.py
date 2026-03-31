import pytest
from src.schemas.core import (
    SolverResult, AllocationDecision, FinalPolicyReport,
    PolicySummary, PolicyExplanation, PolicyAction,
)
from src.policy.translator import translate_decisions, _assign_priority, HIGH_THRESHOLD, MED_THRESHOLD
from src.policy.explainability import (
    explain_solver_selection,
    describe_policy,
    identify_limitations,
    generate_warnings,
    summarise_trade_offs,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_decision(qty=100.0, origin="A", dest="B", cost=None):
    return AllocationDecision(
        origin_port=origin,
        destination_port=dest,
        container_type="20DC",
        quantity_teu=qty,
        departure_period_idx=0,
        arrival_period_idx=1,
        cost=cost if cost is not None else qty * 250.0,
    )


def _make_result(
    name="Heuristic",
    status="feasible",
    svc=0.93,
    unmet=50.0,
    surplus=10.0,
    cost=62500.0,
    decisions=None,
    diagnostics=None,
):
    return SolverResult(
        problem_id="TEST",
        solver_name=name,
        status=status,
        objective_value=cost + 5000.0,
        total_cost=cost,
        service_level=svc,
        unmet_demand_teu=unmet,
        surplus_remaining_teu=surplus,
        solve_time_seconds=0.05,
        decisions=decisions or [_make_decision()],
        diagnostics=diagnostics or {},
    )


# ── translator tests ──────────────────────────────────────────────────────────

class TestTranslator:
    def test_priority_thresholds(self):
        assert _assign_priority(HIGH_THRESHOLD)      == "High"
        assert _assign_priority(MED_THRESHOLD)       == "Medium"
        assert _assign_priority(MED_THRESHOLD - 1.0) == "Low"
        assert _assign_priority(0.0)                 == "Low"

    def test_translate_produces_actions(self):
        result = _make_result(decisions=[
            _make_decision(qty=300.0),   # High
            _make_decision(qty=80.0),    # Medium
            _make_decision(qty=10.0),    # Low
        ])
        actions = translate_decisions(result)
        assert len(actions) == 3
        priorities = [a.priority_level for a in actions]
        assert priorities.index("High")   < priorities.index("Medium")
        assert priorities.index("Medium") < priorities.index("Low")

    def test_action_fields_populated(self):
        result = _make_result(decisions=[_make_decision(qty=250.0, origin="Genoa", dest="Naples")])
        actions = translate_decisions(result)
        a = actions[0]
        assert a.origin_port == "Genoa"
        assert a.destination_port == "Naples"
        assert a.quantity_teu == 250.0
        assert a.action_type == "reposition"
        assert len(a.rationale) > 20

    def test_empty_decisions_returns_empty(self):
        result = _make_result(decisions=[])
        assert translate_decisions(result) == []

    def test_action_id_unique(self):
        result = _make_result(decisions=[_make_decision(), _make_decision()])
        actions = translate_decisions(result)
        ids = [a.action_id for a in actions]
        assert len(ids) == len(set(ids))


# ── explainability tests ───────────────────────────────────────────────────────

class TestExplainability:
    SAMPLE_RANKING = {
        "best_solver": "MILP",
        "ranking_explanation": "MILP ranked first due to optimal status.",
        "trade_off_notes": ["Heuristic had lower cost."],
    }

    def test_solver_selection_explanation(self):
        text = explain_solver_selection(self.SAMPLE_RANKING)
        assert "MILP" in text
        assert len(text) > 20

    def test_policy_description_with_decisions(self):
        result = _make_result(decisions=[_make_decision(qty=200.0)])
        actions = translate_decisions(result)
        desc = describe_policy(actions, result)
        assert "1 repositioning" in desc
        assert "200.0" in desc

    def test_policy_description_no_decisions(self):
        result = _make_result(decisions=[], status="infeasible")
        desc = describe_policy([], result)
        assert "no repositioning actions" in desc.lower()

    def test_limitations_unmet_demand(self):
        result = _make_result(unmet=120.0)
        lims = identify_limitations(result)
        assert any("120.0" in l for l in lims)

    def test_limitations_infeasible(self):
        result = _make_result(status="failed")
        lims = identify_limitations(result)
        assert any("failed" in l for l in lims)

    def test_no_limitations_when_clean(self):
        result = _make_result(unmet=0.0, surplus=0.0, status="optimal")
        lims = identify_limitations(result)
        assert len(lims) == 0

    def test_budget_warning_triggered(self):
        result = _make_result(cost=950_000.0)
        warnings = generate_warnings(result, [], budget_limit=1_000_000.0)
        assert any("Budget" in w for w in warnings)

    def test_no_budget_warning_when_within(self):
        result = _make_result(cost=100_000.0)
        warnings = generate_warnings(result, [], budget_limit=1_000_000.0)
        budget_warns = [w for w in warnings if "Budget" in w]
        assert len(budget_warns) == 0

    def test_low_service_warning(self):
        result = _make_result(svc=0.60)
        warnings = generate_warnings(result, [], budget_limit=1_000_000.0)
        assert any("Service level" in w for w in warnings)

    def test_port_concentration_warning(self):
        # 3 moves all from one source → 100% concentration
        decisions = [_make_decision(origin="A") for _ in range(3)]
        result = _make_result(decisions=decisions)
        actions = translate_decisions(result)
        warnings = generate_warnings(result, actions, budget_limit=1_000_000.0)
        assert any("single port" in w for w in warnings)

    def test_trade_offs_from_summary(self):
        notes = summarise_trade_offs(self.SAMPLE_RANKING)
        assert any("lower cost" in n for n in notes)

    def test_trade_offs_none(self):
        notes = summarise_trade_offs({"trade_off_notes": []})
        assert len(notes) == 1
        assert "No significant" in notes[0]
