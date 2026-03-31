"""
explainability.py
=================
Generates deterministic, template-based explanatory text from structured KPI data.

All text is produced from factual numeric inputs — no probabilistic AI generation.
Every sentence can be traced back to a specific numeric source, making this
suitable for use verbatim in a research paper's results/discussion section.
"""

from collections import Counter
from typing import Any, Dict, List

from src.schemas.core import FinalPolicyReport, PolicyAction, SolverResult
from src.evaluation.solver_eval import STATUS_RANK

BUDGET_WARNING_PCT = 0.90   # Warn if cost exceeds 90% of budget
LOW_SVC_WARNING    = 0.80   # Warn if service level below 80%


# ── solver selection explanation ─────────────────────────────────────────────

def explain_solver_selection(ranking_summary: Dict[str, Any]) -> str:
    """Converts the ranking explanation from Stage 9 into a policy-facing sentence."""
    best = ranking_summary.get("best_solver", "Unknown")
    base = ranking_summary.get("ranking_explanation", "")
    trade_offs = ranking_summary.get("trade_off_notes", [])

    text = f"Solver '{best}' was selected by the evaluation layer. {base}"
    if trade_offs:
        text += " Trade-offs noted: " + " ".join(trade_offs)
    return text.strip()


# ── policy description ────────────────────────────────────────────────────────

def describe_policy(actions: List[PolicyAction], result: SolverResult) -> str:
    """Summarises what the policy physically does in plain language."""
    if not actions:
        return (
            f"Solver '{result.solver_name}' produced no repositioning actions "
            f"(status: {result.status}). No container movements are recommended."
        )

    total_teu = sum(a.quantity_teu for a in actions)
    origins   = Counter(a.origin_port      for a in actions)
    dests     = Counter(a.destination_port for a in actions)

    top_origin = origins.most_common(1)[0]
    top_dest   = dests.most_common(1)[0]

    return (
        f"The policy recommends {len(actions)} repositioning action(s) totalling "
        f"{total_teu:,.1f} TEU. "
        f"The primary source port is '{top_origin[0]}' ({top_origin[1]} move(s)), "
        f"and the primary receiving port is '{top_dest[0]}' ({top_dest[1]} move(s)). "
        f"Expected service level after execution: {result.service_level:.1%}."
    )


# ── limitations ───────────────────────────────────────────────────────────────

def identify_limitations(result: SolverResult) -> List[str]:
    limitations: List[str] = []

    if result.unmet_demand_teu > 0:
        limitations.append(
            f"Residual unmet demand of {result.unmet_demand_teu:,.1f} TEU remains "
            f"after all repositioning actions — full demand coverage was not achievable "
            f"within the given transport network and capacity."
        )

    if result.surplus_remaining_teu > 0:
        limitations.append(
            f"{result.surplus_remaining_teu:,.1f} TEU of surplus containers remain idle "
            f"at origin ports, indicating unused repositioning potential."
        )

    if result.status in ("infeasible", "failed"):
        limitations.append(
            f"Solver returned status '{result.status}'. Results may not represent a "
            f"true optimal or feasible solution. Manual review is recommended."
        )

    return limitations


# ── warnings ──────────────────────────────────────────────────────────────────

def generate_warnings(
    result: SolverResult,
    actions: List[PolicyAction],
    budget_limit: float,
) -> List[str]:
    warnings: List[str] = []

    # Budget pressure
    if budget_limit > 0 and result.total_cost > BUDGET_WARNING_PCT * budget_limit:
        pct_used = result.total_cost / budget_limit * 100
        warnings.append(
            f"Budget utilisation is {pct_used:.1f}% (${result.total_cost:,.0f} of "
            f"${budget_limit:,.0f}). The plan operates close to the budget ceiling."
        )

    # Low service level
    if result.service_level < LOW_SVC_WARNING:
        warnings.append(
            f"Service level is {result.service_level:.1%}, which is below the "
            f"{LOW_SVC_WARNING:.0%} warning threshold. Demand satisfaction is critically low."
        )

    # Port concentration risk
    if actions:
        origins = Counter(a.origin_port for a in actions)
        top_share = origins.most_common(1)[0][1] / len(actions)
        if top_share >= 0.75:
            warnings.append(
                f"{top_share:.0%} of all moves originate from a single port "
                f"('{origins.most_common(1)[0][0]}'). "
                f"This creates a single point of failure in the supply chain."
            )

    # Solver violations
    budget_violations = result.diagnostics.get("budget_violations", [])
    if budget_violations:
        for v in budget_violations:
            warnings.append(f"Constraint violation detected: {v}")

    return warnings


# ── trade-off acceptance notes ────────────────────────────────────────────────

def summarise_trade_offs(ranking_summary: Dict[str, Any]) -> List[str]:
    """Converts Stage 9 trade-off notes into policy-layer acknowledgements."""
    notes = ranking_summary.get("trade_off_notes", [])
    if not notes:
        return ["No significant trade-offs were identified between candidate solvers."]
    return [f"Accepted trade-off: {note}" for note in notes]
