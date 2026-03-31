#!/usr/bin/env python
"""
scripts/run_pipeline.py
=======================
CLI entrypoint for the Empty Container DSS pipeline.

Usage examples
--------------
# Run the full 10-stage pipeline
python scripts/run_pipeline.py --mode full

# Run from a specific stage onward (prior artifacts must exist)
python scripts/run_pipeline.py --mode from_stage --stage optimization

# Run exactly one stage in isolation
python scripts/run_pipeline.py --mode single_stage --stage evaluation

# Validate config and print the execution plan without running anything
python scripts/run_pipeline.py --mode dry_run

# Validate from a specific stage onward
python scripts/run_pipeline.py --mode dry_run --stage forecasting

# Override the config file path
python scripts/run_pipeline.py --mode full --config configs/pipeline_experiment2.yaml
"""

import argparse
import sys
from pathlib import Path

# ── make sure the project root is on sys.path ──────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.logging_utils import setup_logging
from src.orchestrator.pipeline import STAGE_ORDER
from src.orchestrator.runner import execute_pipeline
from src.utils.config import load_config

RESULTS_DIR = PROJECT_ROOT / "results"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Empty Container DSS – Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--mode",
        choices=["full", "from_stage", "single_stage", "dry_run"],
        default="full",
        help="Execution mode (default: full)",
    )
    p.add_argument(
        "--stage",
        choices=STAGE_ORDER,
        default=None,
        help="Target stage for from_stage / single_stage / dry_run modes",
    )
    p.add_argument(
        "--config",
        default="configs/pipeline.yaml",
        help="Path to the pipeline YAML config (default: configs/pipeline.yaml)",
    )
    p.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING"],
        default="INFO",
        help="Console log level (default: INFO)",
    )
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    # ── setup logging ──────────────────────────────────────────────────────
    import logging
    log_level = getattr(logging, args.log_level)
    setup_logging(RESULTS_DIR / "run_log.txt", level=log_level)
    logger = logging.getLogger(__name__)

    # ── load config ────────────────────────────────────────────────────────
    config_path = PROJECT_ROOT / args.config
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))

    # ── resolve mode arguments ─────────────────────────────────────────────
    dry_run     = (args.mode == "dry_run")
    start_stage = args.stage if args.mode == "from_stage"  else None
    only_stage  = args.stage if args.mode == "single_stage" else None

    if args.mode in ("from_stage", "single_stage") and not args.stage:
        logger.error(f"--stage is required when using --mode {args.mode}")
        parser.print_help()
        sys.exit(1)

    # ── run ────────────────────────────────────────────────────────────────
    summary = execute_pipeline(
        mode        = args.mode,
        start_stage = start_stage,
        only_stage  = only_stage,
        dry_run     = dry_run,
        config      = config,
        cwd         = PROJECT_ROOT,
    )

    # ── exit code reflects pipeline status ────────────────────────────────
    if summary.get("status") not in ("success", "dry_run"):
        sys.exit(1)


if __name__ == "__main__":
    main()
