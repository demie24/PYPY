import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.survival_optimizer")

class SurvivalOptimizer:
    """
    Optimizes and ranks dynamic grid survival strategies based on physical parameters
    such as load retention %, voltage stability, line loading margins, and cascade risk.
    """
    def __init__(self):
        # Nominal total demand of loads in the grid is 125 + 90 + 100 = 315 MW
        self.nominal_total_load = 315.0

    def optimize_survival(self, 
                          telemetry: Dict[str, Any], 
                          islands_data: Dict[str, Any],
                          blackstart_active: bool) -> Dict[str, Any]:
        """
        Computes the global grid survivability score and ranks survival strategies.
        """
        if not telemetry:
            return {
                "survivability_score": 0.0,
                "load_retention_pct": 0.0,
                "strategy_ranking": []
            }

        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})

        # 1. Calculate served load MW vs Nominal total
        served_load_mw = 0.0
        for b_name, b_data in buses.items():
            if b_data.get("is_load", False):
                # Count load if voltage is alive
                if b_data.get("voltage_pu", 0.0) > 0.5:
                    served_load_mw += b_data.get("P_mw", 0.0)

        load_retention_pct = (served_load_mw / self.nominal_total_load) * 100.0
        load_retention_pct = min(100.0, max(0.0, load_retention_pct))

        # 2. Voltage stability score
        voltages = [b.get("voltage_pu", 1.0) for b in buses.values() if b.get("voltage_pu", 0.0) > 0.1]
        if voltages:
            mean_dev = sum(abs(v - 1.0) for v in voltages) / len(voltages)
            voltage_score = max(0.0, min(100.0, 100.0 - 200.0 * mean_dev))
        else:
            voltage_score = 0.0

        # 3. Thermal loading headroom score
        loadings = [l.get("capacity_pct", 0.0) for l in lines.values()]
        max_loading = max(loadings) if loadings else 0.0
        if max_loading > 80.0:
            thermal_score = max(0.0, min(100.0, 100.0 - (max_loading - 80.0) * 2.5))
        else:
            thermal_score = 100.0

        # 4. Survivability score formulation
        # Weighted metric reflecting served loads, voltage safety, and loading margin
        survivability_score = (
            0.50 * load_retention_pct +
            0.25 * voltage_score +
            0.25 * thermal_score
        )
        # If grid is fully blacked out, survivability score is 0
        if load_retention_pct < 5.0:
            survivability_score = 0.0

        # 5. Rank survival options statefully
        # Options: NOMINAL, ISLANDING, DEGRADED, BLACKSTART
        strategy_ranking = []

        is_collapsed = all(b.get("voltage_pu", 1.0) < 0.20 for b in buses.values())
        overloaded = any(l > 95.0 for l in loadings)
        unstable = any(b.get("voltage_pu", 1.0) < 0.88 or b.get("voltage_pu", 1.0) > 1.12 for b in buses.values() if b.get("voltage_pu", 0.0) > 0.1)

        if is_collapsed or blackstart_active:
            # Grid is collapsed. Blackstart is the only way out
            strategy_ranking = [
                {"strategy": "BLACKSTART", "score": 90.0, "reason": "Grid collapse detected. Sequential blackstart required."},
                {"strategy": "DEGRADED", "score": 20.0, "reason": "Hold islands offline until blackstart completes."},
                {"strategy": "NOMINAL", "score": 0.0, "reason": "Grid offline. Cannot operate normally."},
                {"strategy": "ISLANDING", "score": 0.0, "reason": "Grid offline. Islanding inactive."}
            ]
        elif overloaded:
            # Overloaded lines risk cascading trips. Islanding or Controlled load shedding (degraded) is preferred
            strategy_ranking = [
                {"strategy": "ISLANDING", "score": 85.0, "reason": "Tripping overloaded lines to prevent collapse cascade."},
                {"strategy": "DEGRADED", "score": 80.0, "reason": "Shed load downstream of overloads to stabilize grid."},
                {"strategy": "NOMINAL", "score": 40.0, "reason": "Overloads active. Nominal path risks cascade."},
                {"strategy": "BLACKSTART", "score": 0.0, "reason": "Grid active. Blackstart not required."}
            ]
        elif unstable:
            # Voltage deviations are present. Rebalancing or local microgrid islanding preferred
            strategy_ranking = [
                {"strategy": "DEGRADED", "score": 85.0, "reason": "Run rebalancing to adjust generator voltage profile."},
                {"strategy": "ISLANDING", "score": 75.0, "reason": "Split unstable zones from healthy grid component."},
                {"strategy": "NOMINAL", "score": 50.0, "reason": "Voltage instability present in nominal topology."},
                {"strategy": "BLACKSTART", "score": 0.0, "reason": "Grid active. Blackstart not required."}
            ]
        else:
            # Everything is nominal
            strategy_ranking = [
                {"strategy": "NOMINAL", "score": 100.0, "reason": "Grid operations stable. Maintain configuration."},
                {"strategy": "DEGRADED", "score": 60.0, "reason": "Nominal state. Degraded load shedding is suboptimal."},
                {"strategy": "ISLANDING", "score": 50.0, "reason": "Nominal state. Splitting would isolate healthy nodes unnecessarily."},
                {"strategy": "BLACKSTART", "score": 0.0, "reason": "Grid active. Blackstart not required."}
            ]

        return {
            "survivability_score": float(round(survivability_score, 2)),
            "load_retention_pct": float(round(load_retention_pct, 2)),
            "strategy_ranking": strategy_ranking
        }
