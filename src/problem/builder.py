import pandas as pd
from typing import Dict, List, Tuple
from datetime import date

from src.schemas.core import ConstraintSet, CapacityContext
from src.problem.models import TransportArc, StructuredProblem

class ProblemBuilder:
    """
    Transforms loosely connected datasets and rule contexts into a unified,
    index-aligned structured matrix specifically tailored for solvers.
    """

    def __init__(self, df_forecasts: pd.DataFrame, cset: ConstraintSet, cctx: CapacityContext):
        self.df_forecasts = df_forecasts
        self.cset = cset
        self.cctx = cctx
        
        # 1. Derive Universal Master Indices maps
        self._date_to_idx, self.time_periods = self._build_time_index()
        self.ports = sorted(list(self.df_forecasts['port'].unique()))
        self.container_types = sorted(list(self.df_forecasts['container_type'].unique()))

    def _build_time_index(self) -> Tuple[Dict[date, int], List[date]]:
        # Sort universally the dates available inside forecasts
        sorted_dates = sorted(self.df_forecasts['target_period'].unique())
        periods = [pd.Timestamp(dt).date() for dt in sorted_dates]
        
        # Merge in any capacity context dates that might extend past standard horizon
        for leg in self.cctx.voyage_legs:
            if leg.departure_time not in periods:
                periods.append(leg.departure_time)
            if leg.arrival_time not in periods:
                periods.append(leg.arrival_time)
                
        # Final universal sort
        unique_sorted = sorted(list(set(periods)))
        return {d: i for i, d in enumerate(unique_sorted)}, unique_sorted

    def _build_matrices(self) -> Tuple[Dict, Dict, Dict]:
        # port -> time_idx -> value
        dem = {p: {t: 0.0 for t in range(len(self.time_periods))} for p in self.ports}
        sup = {p: {t: 0.0 for t in range(len(self.time_periods))} for p in self.ports}
        bal = {p: {t: 0.0 for t in range(len(self.time_periods))} for p in self.ports}
        
        for _, row in self.df_forecasts.iterrows():
            p = row['port']
            t_idx = self._date_to_idx[pd.Timestamp(row['target_period']).date()]
            val = float(row['point_estimate'])
            ftype = row['forecast_type']
            
            if ftype == 'demand':
                dem[p][t_idx] = val
            elif ftype == 'supply':
                sup[p][t_idx] = val
            elif ftype == 'net_balance':
                # Map straight from pure target type resolution
                bal[p][t_idx] = val
                
        return dem, sup, bal

    def _build_network(self) -> Tuple[List[TransportArc], Dict, Dict]:
        arcs = []
        # capacity: origin -> dest -> t_idx -> value
        cap_mat = {p1: {p2: {t: 0.0 for t in range(len(self.time_periods))} for p2 in self.ports} for p1 in self.ports}
        # cost: origin -> dest -> cost  (same-port = 0.0, unknown routes = 0.0)
        cost_mat = {p1: {p2: 0.0 for p2 in self.ports} for p1 in self.ports}
        # Track which routes have been seen so we can min-aggregate
        _seen_cost: Dict = {p1: {p2: None for p2 in self.ports} for p1 in self.ports}

        for leg in self.cctx.voyage_legs:
            if leg.departure_time not in self._date_to_idx or leg.arrival_time not in self._date_to_idx:
                continue

            d_idx = self._date_to_idx[leg.departure_time]
            a_idx = self._date_to_idx[leg.arrival_time]
            o = leg.origin_port
            d = leg.destination_port

            arc = TransportArc(
                origin_port=o,
                destination_port=d,
                mode=leg.mode,
                departure_period_idx=d_idx,
                arrival_period_idx=a_idx,
                capacity_teu=leg.capacity_teu,
                cost_per_teu=leg.cost_per_teu
            )
            arcs.append(arc)

            if o in cap_mat and d in cap_mat[o]:
                # Accumulate multiple modes occurring simultaneously (sea+rail=total cap threshold limits overall if checked manually elsewhere)
                cap_mat[o][d][d_idx] += leg.capacity_teu

            if o in _seen_cost and d in _seen_cost[o]:
                prev = _seen_cost[o][d]
                _seen_cost[o][d] = leg.cost_per_teu if prev is None else min(prev, leg.cost_per_teu)

        # Finalise cost_mat — use seen cost where available, else 0.0
        for p1 in self.ports:
            for p2 in self.ports:
                seen = _seen_cost[p1][p2]
                cost_mat[p1][p2] = float(seen) if seen is not None else 0.0

        return arcs, cap_mat, cost_mat


    def build_problem(self, problem_id: str) -> StructuredProblem:
        dem_mat, sup_mat, bal_mat = self._build_matrices()
        arcs, cap_mat, cost_mat = self._build_network()
        
        # Load initialization zeroed inventory fallback defaults
        init_inv = {p: 0.0 for p in self.ports}

        return StructuredProblem(
            problem_id=problem_id,
            ports=self.ports,
            time_periods=self.time_periods,
            container_types=self.container_types,
            demand_matrix=dem_mat,
            supply_matrix=sup_mat,
            net_balance_matrix=bal_mat,
            arcs=arcs,
            capacity_matrix=cap_mat,
            cost_matrix=cost_mat,
            initial_inventory=init_inv,
            constraint_set=self.cset
        )
