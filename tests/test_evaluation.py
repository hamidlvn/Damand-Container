import pytest
import json
import tempfile
from pathlib import Path
from src.evaluation.solver_eval import evaluate_solvers, result_to_kpi_record, STATUS_RANK
from src.evaluation.ranking import rank_solvers, DEFAULT_RANKING_RULES
from src.evaluation.forecasting_eval import evaluate_forecasts
from src.schemas.core import SolverResult, AllocationDecision


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_solver_result(
    name="Heuristic",
    status="feasible",
    obj=1000.0,
    cost=800.0,
    svc=0.92,
    unmet=50.0,
    surplus=10.0,
    time_s=0.05,
    decisions=None,
    diagnostics=None,
) -> SolverResult:
    return SolverResult(
        problem_id="TEST",
        solver_name=name,
        status=status,
        objective_value=obj,
        total_cost=cost,
        service_level=svc,
        unmet_demand_teu=unmet,
        surplus_remaining_teu=surplus,
        solve_time_seconds=time_s,
        decisions=decisions or [],
        diagnostics=diagnostics or {},
    )


def _write_result_file(result: SolverResult, tmp_dir: Path) -> str:
    path = tmp_dir / f"solver_result_{result.solver_name.lower()}.json"
    path.write_text(result.model_dump_json(indent=4))
    return str(path)


# ── solver_eval tests ──────────────────────────────────────────────────────────

class TestSolverEval:
    def test_single_result_loads(self):
        r = _make_solver_result("Heuristic", status="feasible", unmet=50.0, cost=800.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_result_file(r, Path(tmp))
            ev = evaluate_solvers([path])

        assert "Heuristic" in ev["available_solvers"]
        assert len(ev["solver_kpis"]) == 1
        kpi = ev["solver_kpis"][0]
        assert kpi["status_rank"] == STATUS_RANK["feasible"]
        assert kpi["service_level_pct"] == pytest.approx(92.0)

    def test_missing_file_reported(self):
        ev = evaluate_solvers(["/no/such/file.json"])
        assert len(ev["failed_solvers"]) == 1
        assert len(ev["solver_kpis"]) == 0

    def test_both_solvers_loaded(self):
        h = _make_solver_result("Heuristic", status="feasible", unmet=80.0)
        m = _make_solver_result("MILP",      status="optimal",  unmet=10.0)
        with tempfile.TemporaryDirectory() as tmp:
            hp = _write_result_file(h, Path(tmp))
            mp = _write_result_file(m, Path(tmp))
            ev = evaluate_solvers([hp, mp])

        assert set(ev["available_solvers"]) == {"Heuristic", "MILP"}
        assert len(ev["solver_kpis"]) == 2

    def test_status_rank_ordering(self):
        assert STATUS_RANK["optimal"] < STATUS_RANK["feasible"]
        assert STATUS_RANK["feasible"] < STATUS_RANK["infeasible"]
        assert STATUS_RANK["infeasible"] < STATUS_RANK["failed"]


# ── ranking tests ──────────────────────────────────────────────────────────────

class TestRanking:
    def _kpi(self, solver_name, status, unmet, cost, time_s=0.1):
        r = _make_solver_result(solver_name, status=status, unmet=unmet, cost=cost, time_s=time_s)
        kpi = result_to_kpi_record(r)
        return kpi

    def test_optimal_beats_feasible(self):
        kpis = [
            self._kpi("Heuristic", "feasible", unmet=10.0, cost=500.0),
            self._kpi("MILP",      "optimal",  unmet=20.0, cost=600.0),
        ]
        result = rank_solvers(kpis)
        assert result["best_solver"] == "MILP"   # optimal status wins

    def test_lower_unmet_beats_higher_cost(self):
        """Same status → lower unmet demand wins over lower cost."""
        kpis = [
            self._kpi("A", "feasible", unmet=100.0,  cost=200.0),
            self._kpi("B", "feasible", unmet=5.0,    cost=900.0),
        ]
        result = rank_solvers(kpis)
        assert result["best_solver"] == "B"

    def test_lower_cost_breaks_tie(self):
        """Same status & unmet → lower cost wins."""
        kpis = [
            self._kpi("X", "feasible", unmet=0.0, cost=900.0),
            self._kpi("Y", "feasible", unmet=0.0, cost=300.0),
        ]
        result = rank_solvers(kpis)
        assert result["best_solver"] == "Y"

    def test_faster_solver_breaks_full_tie(self):
        kpis = [
            self._kpi("Slow", "feasible", unmet=0.0, cost=100.0, time_s=10.0),
            self._kpi("Fast", "feasible", unmet=0.0, cost=100.0, time_s=0.1),
        ]
        result = rank_solvers(kpis)
        assert result["best_solver"] == "Fast"

    def test_empty_input(self):
        result = rank_solvers([])
        assert result["best_solver"] is None
        assert result["ranked_solvers"] == []

    def test_single_input(self):
        kpis = [self._kpi("Solo", "feasible", unmet=5.0, cost=100.0)]
        result = rank_solvers(kpis)
        assert result["best_solver"] == "Solo"
        assert result["ranked_solvers"][0]["rank"] == 1

    def test_failed_solver_ranks_last(self):
        kpis = [
            self._kpi("Failed",    "failed",   unmet=0.0, cost=0.0),
            self._kpi("Feasible",  "feasible", unmet=999.0, cost=999999.0),
        ]
        result = rank_solvers(kpis)
        assert result["best_solver"] == "Feasible"

    def test_explanation_is_non_empty(self):
        kpis = [self._kpi("A", "optimal", unmet=0.0, cost=100.0)]
        result = rank_solvers(kpis)
        assert len(result["ranking_explanation"]) > 30

    def test_trade_off_notes_populated(self):
        """Second solver has lower cost → trade-off note should appear."""
        kpis = [
            self._kpi("A", "optimal",  unmet=5.0,  cost=500.0),
            self._kpi("B", "feasible", unmet=50.0, cost=100.0),   # cheaper but more unmet
        ]
        result = rank_solvers(kpis)
        # A ranks first (optimal > feasible), but B has lower cost → note expected
        assert any("lower cost" in note for note in result["trade_off_notes"])


# ── benchmarking mode (single vs both) ───────────────────────────────────────

class TestBenchmarkMode:
    def test_single_mode(self):
        r = _make_solver_result("Heuristic", "feasible", unmet=50.0, cost=300.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_result_file(r, Path(tmp))
            ev = evaluate_solvers([path])
            ranking = rank_solvers(ev["solver_kpis"])

        assert ranking["best_solver"] == "Heuristic"
        assert len(ranking["trade_off_notes"]) == 0   # no second to compare

    def test_benchmark_mode(self):
        h = _make_solver_result("Heuristic", "feasible", unmet=60.0, cost=400.0)
        m = _make_solver_result("MILP",      "optimal",  unmet=5.0,  cost=700.0)
        with tempfile.TemporaryDirectory() as tmp:
            hp = _write_result_file(h, Path(tmp))
            mp = _write_result_file(m, Path(tmp))
            ev = evaluate_solvers([hp, mp])
            ranking = rank_solvers(ev["solver_kpis"])

        assert ranking["best_solver"] == "MILP"
        assert len(ranking["ranked_solvers"]) == 2
