"""
orchestrator/pipeline.py
========================
Defines the canonical stage registry.

Each stage entry specifies:
  - key          : unique stage identifier (used in CLI and dependency graph)
  - display_name : human-readable label for logs and reports
  - fn_path      : dotted path to the callable (resolved at runtime to avoid
                   import-time side effects)
  - depends_on   : stages that must have already run (dependency graph)
  - artifacts    : output files that prove the stage completed successfully
                   (checked during dependency validation)
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class StageSpec:
    key: str
    display_name: str
    fn_path: str                    # e.g. "src.ingestion.loader.ingest_dataset"
    depends_on: List[str]           # stage keys that must precede this one
    artifacts: List[str]            # relative paths under data/processed/ that must exist
    description: str = ""


# ── Canonical stage registry (ordered list) ────────────────────────────────────

STAGES: List[StageSpec] = [
    StageSpec(
        key="ingestion",
        display_name="Stage 1 – Data Ingestion",
        fn_path="src.ingestion.loader.ingest_dataset",
        depends_on=[],
        artifacts=["data/processed/cleaned_history.parquet"],
        description="Loads and validates raw CSV into the HistoricalRecord schema.",
    ),
    StageSpec(
        key="demand",
        display_name="Stage 2 – Demand Management",
        fn_path="src.demand.service.process_demand_layer",
        depends_on=["ingestion"],
        artifacts=[
            "data/processed/historical_signals.parquet",
            "data/processed/historical_net_balance.parquet",
        ],
        description="Derives demand/supply signals and net balance from historical data.",
    ),
    StageSpec(
        key="forecasting",
        display_name="Stage 3 – Forecasting",
        fn_path="src.forecasting.service.generate_forecasts",
        depends_on=["demand"],
        artifacts=[
            "data/processed/forecast_results.parquet",
            "data/processed/model_evaluations.parquet",
        ],
        description="Multi-model forecasting (Theta, HW, RF, Ensemble) per port/type/target.",
    ),
    StageSpec(
        key="constraints",
        display_name="Stage 4 – Constraints Modeling",
        fn_path="src.constraints.service.generate_constraints",
        depends_on=["forecasting"],
        artifacts=["data/processed/business_constraints.json"],
        description="Builds business planning ConstraintSet from config and active port list.",
    ),
    StageSpec(
        key="capacity",
        display_name="Stage 5 – Capacity Modeling",
        fn_path="src.capacity.service.generate_capacity",
        depends_on=["forecasting"],
        artifacts=["data/processed/transport_capacity.json"],
        description="Generates synthetic voyage-level transport capacity network.",
    ),
    StageSpec(
        key="problem_builder",
        display_name="Stage 6 – Problem Builder",
        fn_path="src.problem.service.generate_problem",
        depends_on=["constraints", "capacity"],
        artifacts=["data/processed/structured_problem.json"],
        description="Merges forecasts, constraints, and capacity into a solver-ready StructuredProblem.",
    ),
    StageSpec(
        key="solver_selection",
        display_name="Stage 7 – Solver Selection",
        fn_path="src.solver_selection.service.select_solver",
        depends_on=["problem_builder"],
        artifacts=["data/processed/solver_strategy.json"],
        description="Rule-based selection of MILP / Heuristic / Benchmark strategy.",
    ),
    StageSpec(
        key="optimization",
        display_name="Stage 8 – Optimization Solvers",
        fn_path="src.optimization.runner.run_optimization",
        depends_on=["solver_selection"],
        artifacts=[],   # artifact names depend on which solvers run
        description="Executes Heuristic and/or MILP solvers against StructuredProblem.",
    ),
    StageSpec(
        key="evaluation",
        display_name="Stage 9 – Evaluation",
        fn_path="src.evaluation.service.evaluate_pipeline",
        depends_on=["optimization"],
        artifacts=[
            "data/processed/forecast_evaluation.json",
            "data/processed/solver_evaluation.json",
            "data/processed/evaluation_summary.json",
        ],
        description="Compares forecast models and solver KPIs; produces ranking summary.",
    ),
    StageSpec(
        key="policy",
        display_name="Stage 10 – Policy & Explainability",
        fn_path="src.policy.service.generate_policy",
        depends_on=["evaluation"],
        artifacts=[
            "data/processed/final_policy.json",
            "data/processed/final_policy_report.md",
        ],
        description="Translates best solver result into FinalPolicyReport and Markdown.",
    ),
]

# Lookup by key
STAGE_MAP: Dict[str, StageSpec] = {s.key: s for s in STAGES}
STAGE_ORDER: List[str]          = [s.key for s in STAGES]
