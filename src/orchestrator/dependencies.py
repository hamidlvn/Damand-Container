"""
orchestrator/dependencies.py
============================
Validates that all prerequisite stages and their expected artifacts are
available before a stage is allowed to execute.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from src.orchestrator.pipeline import STAGE_MAP, STAGE_ORDER, StageSpec


class DependencyError(RuntimeError):
    """Raised when a stage's prerequisites are not satisfied."""


def resolve_stage_sequence(
    start_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
) -> List[str]:
    """
    Returns the ordered list of stage keys to run.

    Args:
        start_stage: If provided, runs from this stage onward (inclusive).
        only_stage:  If provided, runs only this single stage (ignores start_stage).
    """
    if only_stage:
        if only_stage not in STAGE_MAP:
            raise ValueError(f"Unknown stage: '{only_stage}'. Valid stages: {STAGE_ORDER}")
        return [only_stage]

    if start_stage:
        if start_stage not in STAGE_MAP:
            raise ValueError(f"Unknown stage: '{start_stage}'. Valid stages: {STAGE_ORDER}")
        idx = STAGE_ORDER.index(start_stage)
        return STAGE_ORDER[idx:]

    return list(STAGE_ORDER)


def validate_dependencies(stage_key: str, cwd: Path = Path(".")) -> List[str]:
    """
    Check that all stages listed in `depends_on` have produced their expected
    artifacts on disk.

    Returns a list of human-readable problem descriptions;
    empty list means all dependencies are satisfied.
    """
    spec: StageSpec = STAGE_MAP[stage_key]
    problems: List[str] = []

    for dep_key in spec.depends_on:
        dep_spec: StageSpec = STAGE_MAP[dep_key]
        for artifact_rel in dep_spec.artifacts:
            artifact_path = cwd / artifact_rel
            if not artifact_path.exists():
                problems.append(
                    f"Stage '{stage_key}' requires '{dep_key}' to have run first, but "
                    f"expected artifact is missing: {artifact_path}"
                )

    return problems


def assert_dependencies(stage_key: str, cwd: Path = Path(".")) -> None:
    """Raises DependencyError with a clear message if any dependency is unsatisfied."""
    problems = validate_dependencies(stage_key, cwd)
    if problems:
        msg = "\n".join(f"  • {p}" for p in problems)
        raise DependencyError(
            f"\nDependency check failed for stage '{stage_key}':\n{msg}\n"
            f"Run the prerequisite stage(s) first or use --mode full."
        )
