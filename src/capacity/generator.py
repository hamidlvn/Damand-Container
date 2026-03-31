import random
import pandas as pd
from typing import List, Dict, Any, Set
from datetime import date

from src.capacity.models import VoyageLeg, CapacityContext

class VoyageGenerator:
    """
    Generates a synthetic time-based physical movement network.
    Constructs a fully-connected port graph multiplied out chronologically 
    across the active planning horizon.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("capacity", {})
        self.min_cap = float(self.config.get("default_min_teu_capacity", 100.0))
        self.max_cap = float(self.config.get("default_max_teu_capacity", 500.0))
        self.min_time = int(self.config.get("default_min_transit_time_periods", 1))
        self.max_time = int(self.config.get("default_max_transit_time_periods", 3))
        self.cost = float(self.config.get("default_cost_per_teu", 250.0))
        
        # Explicit seed for reproducibility
        random.seed(42)

    def _add_periods(self, start_date: date, periods_to_add: int) -> date:
        """Utility for safely incrementing month boundary bounds"""
        # Convert date to tz-naive Timestamp safely, add explicit calendar frequency offsets 
        return (pd.Timestamp(start_date) + pd.DateOffset(months=periods_to_add)).date()

    def generate_voyage_legs(self, unique_ports: Set[str], periods: List[date]) -> List[VoyageLeg]:
        """
        Builds a fully connected directed graph mapping each port to all other ports.
        Explicitly instantiates this matrix uniquely per starting time Period for each active mode.
        """
        explicit_routes = self.config.get("routes", [])
        legs = []
        ports = sorted(list(unique_ports))
        
        # Determine active modes and their configs
        modes_cfg = self.config.get("modes", {})
        active_modes = ["sea"] # Sea is always baseline
        if self.config.get("enable_rail", False):
            active_modes.append("rail")
        if self.config.get("enable_road", False):
            active_modes.append("road")
            
        # Multiply graph out strictly chronologically
        for p_idx, dep_date in enumerate(periods):
            if not explicit_routes:
                # Fully connected synthetic network
                for origin in ports:
                    for destination in ports:
                        if origin != destination:
                            for mode in active_modes:
                                mcfg = modes_cfg.get(mode, {})
                                
                                # Pull ranges with fallbacks
                                c_range = mcfg.get("capacity_range", [self.min_cap, self.max_cap])
                                t_range = mcfg.get("transit_time_range", [self.min_time, self.max_time])
                                cost = float(mcfg.get("cost_per_teu", self.cost))
                                
                                cap = random.uniform(float(c_range[0]), float(c_range[1]))
                                trans_time = random.randint(int(t_range[0]), int(t_range[1]))
                                arr_date = self._add_periods(dep_date, trans_time)
                                
                                leg = VoyageLeg(
                                    origin_port=origin,
                                    destination_port=destination,
                                    mode=mode,
                                    departure_time=dep_date,
                                    arrival_time=arr_date,
                                    capacity_teu=round(cap, 1),
                                    cost_per_teu=cost,
                                    transit_time_periods=trans_time
                                )
                                legs.append(leg)
            else:
                raise NotImplementedError("Parsing explicit route configuration requires specific mapping.")

        return legs

    def build_context(self, voyage_legs: List[VoyageLeg]) -> CapacityContext:
        """
        Assembles all discrete dynamic legs into a comprehensive Capacity Context limitation scope.
        """
        g_limit = self.config.get("global_teu_capacity_limit", None)
        if g_limit is not None:
            g_limit = float(g_limit)
            
        return CapacityContext(
            voyage_legs=voyage_legs,
            global_teu_capacity_limit=g_limit
        )
