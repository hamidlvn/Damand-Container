"""
tests/test_orchestrator.py
==========================
Tests for the orchestrator layer (pipeline, dependencies, runner).
These tests use monkeypatching/mocking so they don't require real data artifacts.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.orchestrator.pipeline import STAGE_ORDER, STAGE_MAP
from src.orchestrator.dependencies import (
    resolve_stage_sequence,
    validate_dependencies,
    DependencyError,
    assert_dependencies,
)
from src.orchestrator.runner import execute_pipeline


# ── resolve_stage_sequence ────────────────────────────────────────────────────

class TestResolveStageSequence:
    def test_full_returns_all(self):
        seq = resolve_stage_sequence()
        assert seq == STAGE_ORDER

    def test_from_stage_returns_suffix(self):
        seq = resolve_stage_sequence(start_stage="optimization")
        idx = STAGE_ORDER.index("optimization")
        assert seq == STAGE_ORDER[idx:]

    def test_single_stage(self):
        seq = resolve_stage_sequence(only_stage="evaluation")
        assert seq == ["evaluation"]

    def test_only_stage_overrides_start(self):
        seq = resolve_stage_sequence(start_stage="ingestion", only_stage="policy")
        assert seq == ["policy"]

    def test_unknown_stage_raises(self):
        with pytest.raises(ValueError, match="Unknown stage"):
            resolve_stage_sequence(start_stage="nonexistent")

    def test_unknown_only_raises(self):
        with pytest.raises(ValueError, match="Unknown stage"):
            resolve_stage_sequence(only_stage="ghost")


# ── validate_dependencies ─────────────────────────────────────────────────────

class TestValidateDependencies:
    def test_ingestion_has_no_deps(self):
        """Ingestion depends on nothing → always passes."""
        with tempfile.TemporaryDirectory() as tmp:
            problems = validate_dependencies("ingestion", cwd=Path(tmp))
        assert problems == []

    def test_demand_fails_without_ingestion_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = validate_dependencies("demand", cwd=Path(tmp))
        # cleaned_history.parquet is missing
        assert any("cleaned_history.parquet" in p for p in problems)

    def test_demand_passes_when_artifact_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create the required artifact
            artifact = Path(tmp) / "data" / "processed" / "cleaned_history.parquet"
            artifact.parent.mkdir(parents=True)
            artifact.touch()
            problems = validate_dependencies("demand", cwd=Path(tmp))
        assert problems == []

    def test_assert_dependencies_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(DependencyError, match="cleaned_history.parquet"):
                assert_dependencies("demand", cwd=Path(tmp))


# ── execute_pipeline (full dry_run) ──────────────────────────────────────────

class TestExecutePipeline:
    BASE_CONFIG = {
        "reproducibility": {"random_seed": 42},
        "ingestion": {"raw_data_path": "/tmp/fake.csv"},
    }

    def test_dry_run_full(self):
        summary = execute_pipeline(
            mode="full",
            dry_run=True,
            config=self.BASE_CONFIG,
        )
        assert summary["status"] == "dry_run"
        assert len(summary["stages_executed"]) == len(STAGE_ORDER)
        assert all(s["status"] == "dry_run" for s in summary["stages_executed"])

    def test_dry_run_single_stage(self):
        summary = execute_pipeline(
            mode="single_stage",
            only_stage="evaluation",
            dry_run=True,
            config=self.BASE_CONFIG,
        )
        assert summary["status"] == "dry_run"
        assert len(summary["stages_executed"]) == 1
        assert summary["stages_executed"][0]["stage"] == "evaluation"

    def test_dry_run_from_stage(self):
        summary = execute_pipeline(
            mode="from_stage",
            start_stage="optimization",
            dry_run=True,
            config=self.BASE_CONFIG,
        )
        stages_run = [s["stage"] for s in summary["stages_executed"]]
        assert "optimization" in stages_run
        assert "ingestion" not in stages_run
        assert "demand" not in stages_run

    def test_unknown_start_stage_returns_failed(self):
        summary = execute_pipeline(
            mode="from_stage",
            start_stage="ghost_stage",
            dry_run=True,
            config=self.BASE_CONFIG,
        )
        assert summary["status"] == "failed"
        assert any("Unknown" in e for e in summary["errors"])

    def test_run_summary_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.orchestrator.runner.RESULTS_DIR", Path(tmp)):
                summary = execute_pipeline(
                    mode="full",
                    dry_run=True,
                    config=self.BASE_CONFIG,
                )
            saved = Path(tmp) / "run_summary.json"
            assert saved.exists()
            data = json.loads(saved.read_text())
            assert data["status"] == "dry_run"

    def test_dependency_failure_halts_pipeline(self):
        """
        Run ingestion in live mode (not dry_run) with a mocked stage function
        that succeeds, but demand management should fail because ingestion
        artifacts don't exist on disk.
        """
        def mock_ingest(config=None):
            # Does NOT write any artifact to disk
            pass

        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("src.orchestrator.runner.RESULTS_DIR", Path(tmp)),
                patch("src.orchestrator.runner._resolve_fn", return_value=mock_ingest),
            ):
                summary = execute_pipeline(
                    mode="from_stage",
                    start_stage="demand",   # depends on ingestion artifact
                    dry_run=False,
                    config=self.BASE_CONFIG,
                    cwd=Path(tmp),
                )
        assert summary["status"] == "failed"
        assert any("cleaned_history.parquet" in e for e in summary["errors"])
