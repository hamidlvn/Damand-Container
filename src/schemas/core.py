from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date

# 1. Historical Data
class HistoricalRecord(BaseModel):
    """Represents a single row of raw historical port activity."""
    date: date
    port: str
    container_type: str
    empty_out_teu: float = Field(..., description="Empty containers moved out (Demand proxy)")
    empty_in_teu: float = Field(..., description="Empty containers moved in (Supply proxy)")
    full_out_teu: Optional[float] = None
    full_in_teu: Optional[float] = None

# 2. Demand & Supply Signals
class DemandSupplySignal(BaseModel):
    """Processed business signal for a specific port/type/period."""
    period: date
    port: str
    container_type: str
    inferred_demand: float
    inferred_supply: float
    criticality_score: float = Field(0.0, description="Priority score for demand fulfillment")

# 3. Net Balance
class NetBalance(BaseModel):
    """Derived shortage or surplus state."""
    period: date
    port: str
    container_type: str
    balance: float = Field(..., description="Positive means surplus, negative means shortage.")
    is_shortage: bool
    is_surplus: bool

# 4. Forecast Results
class ForecastResult(BaseModel):
    """Output from the Forecasting Layer."""
    target_period: date
    port: str
    container_type: str
    forecast_type: str = Field(..., description="'demand', 'supply', or 'net_balance'")
    model_name: str
    point_estimate: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

# 5. Capacity Context
class VoyageLeg(BaseModel):
    """Represents a specific time-bound voyage capacity."""
    origin_port: str
    destination_port: str
    mode: str = Field(default="sea", pattern="^(sea|rail|road)$", description="Mode of transport")
    departure_time: date = Field(..., description="When the voyage leaves the origin")
    arrival_time: date = Field(..., description="When the voyage arrives at the destination")
    capacity_teu: float = Field(..., description="Maximum TEU that can be moved on this specific voyage")
    cost_per_teu: float = Field(..., description="Cost to move one TEU on this leg")
    transit_time_periods: int = Field(..., description="Number of periods the transit takes")

class CapacityContext(BaseModel):
    """Dynamic transport capacity network structure over time."""
    voyage_legs: List[VoyageLeg]
    global_teu_capacity_limit: Optional[float] = Field(None, description="System-wide transport capacity limit across all routes")

# 6. Constraint Sets
class PortConstraint(BaseModel):
    port: str
    min_inventory: float = Field(0.0, description="Hard minimum safety stock")
    max_inventory: float = Field(999999.0, description="Finite mathematical upper bound placeholder, not a physical real-world capacity")
    priority_weight: float = Field(1.0, description="Extensible priority weight (e.g., static, shortage-driven, or strategic)")
    service_level_target: Optional[float] = Field(None, description="Optional per-port override for required percentage of demand satisfaction")

class BudgetConstraint(BaseModel):
    is_hard_limit: bool = Field(..., description="If True, budget cannot be violated. If False, budget is a soft target with a cost penalty.")
    limit_value: float = Field(..., description="The budget ceiling for total repositioning cost")
    violation_penalty_per_unit: Optional[float] = Field(None, description="The penalty multiplier for every dollar over budget (used only if is_hard_limit is False)")

class ConstraintSet(BaseModel):
    """Business and planning constraints applied during optimization."""
    port_constraints: List[PortConstraint]
    global_service_level_target: float = Field(0.90, description="Global soft constraint: required percentage of demand satisfaction globally")
    budget: BudgetConstraint
    shortage_penalty: float = Field(100.0, description="Penalty cost per TEU of unmet demand")
    surplus_penalty: float = Field(50.0, description="Penalty cost per TEU of excess inventory")
    global_max_moves_teu: Optional[float] = Field(None, description="Hard limit on total sum of TEU repositioned across the entire system")

# 7. Structured Problem
class TransportArc(BaseModel):
    """Indexed solver-friendly representation of a valid transport voyage."""
    origin_port: str
    destination_port: str
    mode: str = Field(default="sea", description="Mode of transport (sea/rail/road)")
    departure_period_idx: int
    arrival_period_idx: int
    capacity_teu: float
    cost_per_teu: float

class StructuredProblem(BaseModel):
    """The unified tensor/matrix layout interface explicitly formatted for Optimization Solvers."""
    problem_id: str
    ports: List[str]
    time_periods: List[date]
    container_types: List[str]
    
    # Port-Time Matrices: port -> dict(time_idx -> value)
    demand_matrix: Dict[str, Dict[int, float]]
    supply_matrix: Dict[str, Dict[int, float]]
    net_balance_matrix: Dict[str, Dict[int, float]]
    
    # Edges/Routing
    arcs: List[TransportArc]
    
    # Edge Matrices: origin -> destination -> time_idx -> value
    capacity_matrix: Dict[str, Dict[str, Dict[int, float]]]
    
    # Distance/Cost base lookup: origin -> destination -> cost
    cost_matrix: Dict[str, Dict[str, float]]
    
    # Initial state (Fallback to 0 if unknown)
    initial_inventory: Dict[str, float]
    
    # Original Constraint Rules
    constraint_set: ConstraintSet

# 8. Allocation Decisions
class AllocationDecision(BaseModel):
    """A single recommended movement from the solver."""
    origin_port: str
    destination_port: str
    mode: str = Field(default="sea", description="Transport mode selected by the solver")
    container_type: str
    quantity_teu: float
    departure_period_idx: int
    arrival_period_idx: int
    cost: float = Field(..., description="Total transport cost for this move (quantity * cost_per_teu)")

# 9. Solver Results
class SolverResult(BaseModel):
    """Standardized output from any solver backend."""
    problem_id: str
    solver_name: str
    status: str = Field(..., description="'optimal', 'feasible', 'infeasible', or 'failed'")
    objective_value: float
    total_cost: float = Field(..., description="Sum of all transport costs across decisions")
    service_level: float = Field(..., description="Fraction of total demand that was met (0.0–1.0)")
    unmet_demand_teu: float
    surplus_remaining_teu: float
    solve_time_seconds: float
    decisions: List[AllocationDecision]
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Violated assumptions, fallback used, warnings, etc.")

# 10. Solver Selection Strategy
class SolverStrategy(BaseModel):
    """Decision layer instruction detailing which optimization algorithms should run."""
    problem_id: str
    selected_solver: List[str] = Field(..., description="E.g., ['MILP'], ['Heuristic'], or both for benchmarking.")
    execution_mode: str = Field(..., description="'single' or 'benchmark'")
    fallback_solver: Optional[str] = Field(None, description="Secondary solver if primary fails")
    reasoning: str = Field(..., description="Explanation of why this strategy was selected based on extracted features.")
    runtime_hint: str = Field(..., description="'low', 'medium', or 'high' complexity estimate")

# 11. Policy Reports
class PolicyAction(BaseModel):
    """A single translated, human-facing repositioning recommendation."""
    action_id: str
    action_type: str = Field("reposition", description="Type of action: 'reposition'")
    origin_port: str
    destination_port: str
    mode: str = Field(default="sea", description="Transport mode to execute the repositioning")
    container_type: str
    quantity_teu: float
    departure_period_idx: int
    arrival_period_idx: int
    estimated_cost: float
    priority_level: str = Field(..., description="'High', 'Medium', or 'Low'")
    rationale: str = Field(..., description="Short rule-based explanation for this specific action")

class PolicySummary(BaseModel):
    total_repositioned_teu: float
    total_estimated_cost: float
    expected_service_level: float
    remaining_unmet_demand_teu: float
    remaining_surplus_teu: float

class PolicyExplanation(BaseModel):
    solver_selection_reason: str
    policy_description: str
    limitations: List[str]
    warnings: List[str]
    trade_offs_accepted: List[str]

class FinalPolicyReport(BaseModel):
    """Complete machine-readable policy artifact for the final stage."""
    report_id: str
    problem_id: str
    generated_at: str
    policy_status: str = Field(..., description="'active', 'partial', or 'infeasible'")
    selected_solver: str
    actions: List[PolicyAction]
    summary: PolicySummary
    explanation: PolicyExplanation
