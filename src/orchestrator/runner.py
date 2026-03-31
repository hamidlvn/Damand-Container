"""
orchestrator/runner.py
======================
Execution engine.  Calls each stage function in dependency-safe order,
applies the configured random seed, tracks timing per stage,
and produces a structured RunSummary artifact.
"""

import importlib
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.orchestrator.pipeline import STAGE_MAP, StageSpec
from src.orchestrator.dependencies import assert_dependencies, DependencyError, resolve_stage_sequence
from src.utils.config import load_config

logger = logging.getLogger(__name__)

RESULTS_DIR = Path("results")


# ── run summary dataclass (plain dict for JSON portability) ───────────────────

def _make_summary(
    run_id: str,
    mode: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "run_id":           run_id,
        "mode":             mode,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "dataset_path":     config.get("ingestion", {}).get("raw_data_path", "unknown"),
        "stages_executed":  [],
        "stages_skipped":   [],
        "status":           "running",
        "duration_seconds": 0.0,
        "output_artifacts": [],
        "errors":           [],
    }


def _collect_artifacts(stages: List[str]) -> List[str]:
    """Returns all artifact paths expected by the given stages."""
    artifacts = []
    for key in stages:
        spec = STAGE_MAP[key]
        artifacts.extend(spec.artifacts)
    return artifacts


def _resolve_fn(fn_path: str):
    """Dynamically import and return the stage callable."""
    module_path, fn_name = fn_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, fn_name)


def _apply_seed(config: Dict[str, Any]) -> int:
    """Reads the configured seed and applies it to Python random + numpy if available."""
    seed = config.get("reproducibility", {}).get("random_seed", 42)
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    logger.info(f"Random seed applied: {seed}")
    return seed


# ── core execution ─────────────────────────────────────────────────────────────

def execute_pipeline(
    mode: str = "full",
    start_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
    dry_run: bool = False,
    config: Dict[str, Any] = None,
    cwd: Path = Path("."),
) -> Dict[str, Any]:
    """
    Main execution entry point.

    Modes
    -----
    full         – run all 10 stages in order
    from_stage   – run from `start_stage` onward (requires artifact hand-offs)
    single_stage – run only `only_stage`
    dry_run      – validate config + dependencies, print plan, do NOT execute

    Returns the run summary dict (also saved to results/run_summary.json).
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if config is None:
        config = load_config()

    run_id  = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    summary = _make_summary(run_id, mode, config)
    t_global_start = time.time()

    seed = _apply_seed(config)
    summary["random_seed"] = seed

    # Resolve which stages to run
    try:
        stage_sequence = resolve_stage_sequence(
            start_stage=start_stage,
            only_stage=only_stage,
        )
    except ValueError as e:
        summary["status"] = "failed"
        summary["errors"].append(str(e))
        _save_summary(summary)
        logger.error(str(e))
        return summary

    all_known = set(STAGE_MAP.keys())
    skipped   = [s for s in STAGE_MAP if s not in stage_sequence]
    summary["stages_skipped"] = skipped

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Run {run_id} | mode={mode} | stages={stage_sequence}")

    # ── stage loop ─────────────────────────────────────────────────────────
    for stage_key in stage_sequence:
        spec: StageSpec = STAGE_MAP[stage_key]

        # Dependency guard (skip in dry_run – we just show the plan)
        if not dry_run:
            try:
                assert_dependencies(stage_key, cwd)
            except DependencyError as e:
                msg = str(e)
                logger.error(msg)
                summary["errors"].append(msg)
                summary["status"] = "failed"
                _save_summary(summary)
                return summary

        logger.info(f"{'[DRY] ' if dry_run else ''}▶  {spec.display_name}")

        if dry_run:
            summary["stages_executed"].append({"stage": stage_key, "status": "dry_run"})
            continue

        # ── execute ────────────────────────────────────────────────────────
        t_stage_start = time.time()
        try:
            fn = _resolve_fn(spec.fn_path)
            fn(config=config)
            elapsed = round(time.time() - t_stage_start, 3)
            logger.info(f"  ✓ {spec.display_name} completed in {elapsed}s")
            summary["stages_executed"].append({"stage": stage_key, "status": "ok", "duration_s": elapsed})

        except Exception as exc:
            elapsed = round(time.time() - t_stage_start, 3)
            msg = f"Stage '{stage_key}' failed after {elapsed}s: {exc}"
            logger.exception(msg)
            summary["errors"].append(msg)
            summary["status"] = "failed"
            summary["stages_executed"].append({"stage": stage_key, "status": "failed", "duration_s": elapsed, "error": str(exc)})
            _save_summary(summary)
            return summary

    # ── finalise ───────────────────────────────────────────────────────────
    summary["duration_seconds"] = round(time.time() - t_global_start, 3)
    summary["output_artifacts"] = _collect_artifacts(stage_sequence)
    summary["status"]           = "dry_run" if dry_run else "success"

    _save_summary(summary)

    if not dry_run:
        logger.info(
            f"\n{'='*60}\n"
            f"  Run {run_id} COMPLETE\n"
            f"  Stages: {len(summary['stages_executed'])} executed | "
            f"{len(skipped)} skipped\n"
            f"  Duration: {summary['duration_seconds']}s\n"
            f"  Status: {summary['status'].upper()}\n"
            f"{'='*60}"
        )
    return summary


def _save_summary(summary: Dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "run_summary.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=4, default=str)
