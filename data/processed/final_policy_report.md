# Empty Container Repositioning Policy Report

| Field | Value |
|---|---|
| Report ID | `REPORT-77360FB5` |
| Problem ID | `PROB-12089c7b` |
| Generated | 2026-04-02T08:41:28.802878 |
| Policy Status | **PARTIAL** |
| Selected Solver | Heuristic |

---

## Executive Summary

Solver 'Heuristic' produced no repositioning actions (status: feasible). No container movements are recommended.

---

## Policy Summary KPIs

| KPI | Value |
|---|---|
| Total Repositioned TEU | 0.0 |
| Total Estimated Cost | $0.00 |
| Expected Service Level | 74.7% |
| Remaining Unmet Demand | 183,337.9 TEU |
| Remaining Surplus | 0.0 TEU |

---

## Solver Selection Rationale

Solver 'Heuristic' was selected by the evaluation layer. 'Heuristic' ranked first based on the following priority rules (applied lexicographically): feasibility status, unmet demand (TEU), total transport cost, solve time. It achieved status='feasible', unmet_demand=183337.91 TEU, cost=$0.00, service_level=74.72%.

---

## Recommended Actions

| # | Priority | Origin → Destination | Qty (TEU) | Depart T | Arrive T | Est. Cost |
|---|---|---|---|---|---|---|

---

## Limitations

- Residual unmet demand of 183,337.9 TEU remains after all repositioning actions — full demand coverage was not achievable within the given transport network and capacity.

## Warnings

- ⚠️ Service level is 74.7%, which is below the 80% warning threshold. Demand satisfaction is critically low.

## Trade-offs Accepted

- No significant trade-offs were identified between candidate solvers.