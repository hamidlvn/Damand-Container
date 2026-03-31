"""
policy/service.py
=================
Stage 10 orchestrator. Loads all upstream artifacts and produces:
  data/processed/final_policy.json     – machine-readable FinalPolicyReport
  data/processed/final_policy_report.md – human-readable Markdown summary
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.utils.config import load_config
from src.schemas.core import SolverResult, ConstraintSet, FinalPolicyReport, PolicySummary, PolicyExplanation
from src.policy.translator import translate_decisions
from src.policy.explainability import (
    explain_solver_selection,
    describe_policy,
    identify_limitations,
    generate_warnings,
    summarise_trade_offs,
)

logger = logging.getLogger(__name__)


def generate_policy(config: Dict[str, Any] = None) -> None:
    if config is None:
        config = load_config()

    processed_dir = Path("data/processed")
    po_cfg = config.get("policy", {})
    ev_cfg = config.get("evaluation", {})

    # ── load evaluation summary (Stage 9) ────────────────────────────────
    summary_file = processed_dir / ev_cfg.get("output_summary", "evaluation_summary.json")
    if not summary_file.exists():
        logger.error("Stage 10 requires evaluation_summary.json from Stage 9. Aborting.")
        return

    with open(summary_file, "r") as f:
        eval_summary: Dict[str, Any] = json.load(f)

    best_solver_name: str = eval_summary.get("best_solver")
    if not best_solver_name:
        logger.error("No best_solver identified in evaluation_summary. Aborting.")
        return

    logger.info(f"Stage 10 – Policy generation. Best solver: {best_solver_name}")

    # ── load corresponding SolverResult (Stage 8) ─────────────────────────
    result_file = processed_dir / f"solver_result_{best_solver_name.lower()}.json"
    if not result_file.exists():
        logger.error(f"SolverResult for '{best_solver_name}' not found at {result_file}. Aborting.")
        return

    with open(result_file, "r") as f:
        result = SolverResult.model_validate_json(f.read())

    # ── load budget limit for warning thresholds (Stage 4) ───────────────
    budget_limit = 1_000_000.0   # default fallback
    constraints_file = processed_dir / config.get("constraints", {}).get(
        "output_constraints_file", "business_constraints.json"
    )
    if constraints_file.exists():
        with open(constraints_file, "r") as f:
            cset = ConstraintSet.model_validate_json(f.read())
        budget_limit = cset.budget.limit_value

    # ── translate decisions to policy actions ─────────────────────────────
    actions = translate_decisions(result)

    # ── compute policy summary ────────────────────────────────────────────
    summary = PolicySummary(
        total_repositioned_teu=round(sum(a.quantity_teu for a in actions), 2),
        total_estimated_cost=round(sum(a.estimated_cost for a in actions), 2),
        expected_service_level=result.service_level,
        remaining_unmet_demand_teu=result.unmet_demand_teu,
        remaining_surplus_teu=result.surplus_remaining_teu,
    )

    # ── build explainability block ─────────────────────────────────────────
    explanation = PolicyExplanation(
        solver_selection_reason=explain_solver_selection(eval_summary),
        policy_description=describe_policy(actions, result),
        limitations=identify_limitations(result),
        warnings=generate_warnings(result, actions, budget_limit),
        trade_offs_accepted=summarise_trade_offs(eval_summary),
    )

    # ── determine policy status ──────────────────────────────────────────
    if result.status in ("optimal", "feasible", "feasible_with_violations"):
        if result.unmet_demand_teu > 0:
            policy_status = "partial"
        else:
            policy_status = "active"
    else:
        policy_status = "infeasible"

    # ── assemble the report ───────────────────────────────────────────────
    report = FinalPolicyReport(
        report_id=f"REPORT-{uuid.uuid4().hex[:8].upper()}",
        problem_id=result.problem_id,
        generated_at=datetime.utcnow().isoformat(),
        policy_status=policy_status,
        selected_solver=best_solver_name,
        actions=actions,
        summary=summary,
        explanation=explanation,
    )

    # ── persist JSON ──────────────────────────────────────────────────────
    json_out = processed_dir / po_cfg.get("output_policy_json", "final_policy.json")
    with open(json_out, "w") as f:
        f.write(report.model_dump_json(indent=4))
    logger.info(f"  Policy JSON saved → {json_out}")

    # ── persist Markdown ──────────────────────────────────────────────────
    md_out = processed_dir / po_cfg.get("output_policy_md", "final_policy_report.md")
    with open(md_out, "w", encoding="utf-8") as f:
        f.write(_render_markdown(report))
    logger.info(f"  Policy Markdown saved → {md_out}")

    logger.info(
        f"Stage 10 complete. "
        f"Status={policy_status} | Actions={len(actions)} | "
        f"TEU={summary.total_repositioned_teu:,.1f} | "
        f"Cost=${summary.total_estimated_cost:,.0f} | "
        f"SvcLevel={summary.expected_service_level:.1%}"
    )


# ── Markdown renderer ─────────────────────────────────────────────────────────

def _render_markdown(r: FinalPolicyReport) -> str:
    s = r.summary
    e = r.explanation
    lines = [
        f"# Empty Container Repositioning Policy Report",
        f"",
        f"| Field | Value |",
        f"|---|---|",
        f"| Report ID | `{r.report_id}` |",
        f"| Problem ID | `{r.problem_id}` |",
        f"| Generated | {r.generated_at} |",
        f"| Policy Status | **{r.policy_status.upper()}** |",
        f"| Selected Solver | {r.selected_solver} |",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"{e.policy_description}",
        f"",
        f"---",
        f"",
        f"## Policy Summary KPIs",
        f"",
        f"| KPI | Value |",
        f"|---|---|",
        f"| Total Repositioned TEU | {s.total_repositioned_teu:,.1f} |",
        f"| Total Estimated Cost | ${s.total_estimated_cost:,.2f} |",
        f"| Expected Service Level | {s.expected_service_level:.1%} |",
        f"| Remaining Unmet Demand | {s.remaining_unmet_demand_teu:,.1f} TEU |",
        f"| Remaining Surplus | {s.remaining_surplus_teu:,.1f} TEU |",
        f"",
        f"---",
        f"",
        f"## Solver Selection Rationale",
        f"",
        f"{e.solver_selection_reason}",
        f"",
        f"---",
        f"",
        f"## Recommended Actions",
        f"",
        f"| # | Priority | Origin → Destination | Qty (TEU) | Depart T | Arrive T | Est. Cost |",
        f"|---|---|---|---|---|---|---|",
    ]
    for i, a in enumerate(r.actions, 1):
        lines.append(
            f"| {i} | {a.priority_level} | {a.origin_port} → {a.destination_port} "
            f"| {a.quantity_teu:,.1f} | {a.departure_period_idx} | {a.arrival_period_idx} "
            f"| ${a.estimated_cost:,.2f} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Limitations",
        f"",
    ]
    lines += [f"- {l}" for l in e.limitations] or ["- None identified."]

    lines += [
        f"",
        f"## Warnings",
        f"",
    ]
    lines += [f"- ⚠️ {w}" for w in e.warnings] or ["- None."]

    lines += [
        f"",
        f"## Trade-offs Accepted",
        f"",
    ]
    lines += [f"- {t}" for t in e.trade_offs_accepted]

    return "\n".join(lines)
