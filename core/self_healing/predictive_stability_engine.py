import os
import sys
import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.predictive_stability")

class PredictiveStabilityEngine:
    """
    Predicts grid instability propagation trajectories, forecasts voltage/frequency collapse probability,
    estimates survivability horizons, and predicts line overload cascading.
    """
    def __init__(self, history_len: int = 5):
        self.history_len = history_len
        self.telemetry_history: List[Dict[str, Any]] = []

    def update_history(self, telemetry: Dict[str, Any]):
        if not telemetry:
            return
        self.telemetry_history.append(telemetry)
        if len(self.telemetry_history) > self.history_len:
            self.telemetry_history.pop(0)

    def evaluate_predictive_stability(self, telemetry: Dict[str, Any], active_islands: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes the trajectory of voltages, frequencies, and capacities.
        Returns:
            - collapse_probability: float (0 - 100)
            - survivability_horizon: float (seconds remaining, 999 if stable)
            - predicted_overloads: List[Dict[str, Any]]
            - propagation_trajectory: List[str] (sequence of bus/line failures)
        """
        self.update_history(telemetry)
        
        if len(self.telemetry_history) < 2:
            return {
                "collapse_probability": 0.0,
                "survivability_horizon": 999.0,
                "predicted_overloads": [],
                "propagation_trajectory": []
            }

        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})

        prev_state = self.telemetry_history[-2].get("state", {})
        prev_buses = prev_state.get("buses", {})
        prev_lines = prev_state.get("lines", {})

        # 1. Voltage decay prediction
        voltage_collapse_risk = 0.0
        min_v_horizon = 999.0
        voltage_propagation = []
        
        for bus_name, bus_data in buses.items():
            curr_v = bus_data.get("voltage_pu", 1.0)
            prev_v = prev_buses.get(bus_name, {}).get("voltage_pu", 1.0)
            dv_dt = curr_v - prev_v  # step interval is 1s, so dv/dt = delta_v
            
            if dv_dt < -0.005 and curr_v < 0.95:
                # Voltage is decaying. Calculate time to reach collapse threshold (0.85)
                remaining_margin = curr_v - 0.85
                if remaining_margin > 0:
                    time_to_collapse = remaining_margin / abs(dv_dt)
                    min_v_horizon = min(min_v_horizon, time_to_collapse)
                    voltage_propagation.append((bus_name, time_to_collapse))
                else:
                    min_v_horizon = 0.0
                    voltage_propagation.append((bus_name, 0.0))

        # 2. Line overload propagation prediction
        predicted_overloads = []
        min_line_horizon = 999.0
        line_propagation = []

        for line_id, line_data in lines.items():
            curr_cap = line_data.get("capacity_pct", 0.0)
            prev_cap = prev_lines.get(line_id, {}).get("capacity_pct", 0.0)
            dc_dt = curr_cap - prev_cap
            
            # If line loading is high or rising fast
            if curr_cap > 80.0 or (dc_dt > 1.0 and curr_cap > 50.0):
                remaining_margin = 110.0 - curr_cap
                if remaining_margin > 0 and dc_dt > 0:
                    time_to_overload = remaining_margin / dc_dt
                    min_line_horizon = min(min_line_horizon, time_to_overload)
                    predicted_overloads.append({
                        "line_id": line_id,
                        "current_loading": curr_cap,
                        "predicted_time_to_trip": round(time_to_overload, 1)
                    })
                    line_propagation.append((line_id, time_to_overload))
                elif curr_cap >= 110.0:
                    min_line_horizon = 0.0
                    predicted_overloads.append({
                        "line_id": line_id,
                        "current_loading": curr_cap,
                        "predicted_time_to_trip": 0.0
                    })
                    line_propagation.append((line_id, 0.0))

        # 3. Frequency collapse prediction
        min_freq_horizon = 999.0
        freq_collapse_risk = 0.0
        if active_islands:
            # Check frequencies from active islands
            # Balancer publishes frequencies statefully. We can extract it from telemetry
            balancing_data = telemetry.get("ai_prediction", {}) # Or check telemetry frequencies
            # Frequencies are also stored in bus parameters
            for bus_name, bus_data in buses.items():
                freq = bus_data.get("frequency_hz", 60.0)
                prev_freq = prev_buses.get(bus_name, {}).get("frequency_hz", 60.0)
                df_dt = freq - prev_freq
                
                if df_dt < -0.05 and freq < 59.5:
                    remaining_margin = freq - 57.5
                    if remaining_margin > 0:
                        time_to_collapse = remaining_margin / abs(df_dt)
                        min_freq_horizon = min(min_freq_horizon, time_to_collapse)
                    else:
                        min_freq_horizon = 0.0

        # Determine overall survivability horizon
        survivability_horizon = min(min_v_horizon, min_line_horizon, min_freq_horizon)
        if survivability_horizon > 300.0:
            survivability_horizon = 999.0

        # Calculate collapse probability based on horizon and current stress metrics
        # Horizon < 10s -> high probability. Horizon > 60s -> low.
        if survivability_horizon == 0.0:
            collapse_probability = 100.0
        elif survivability_horizon < 15.0:
            collapse_probability = 90.0 - 3.0 * survivability_horizon
        elif survivability_horizon < 60.0:
            collapse_probability = 50.0 - 0.5 * (survivability_horizon - 15.0)
        else:
            # Fallback to general indicators
            stress_points = 0.0
            for line_id, line_data in lines.items():
                if line_data.get("capacity_pct", 0.0) > 90.0:
                    stress_points += 20.0
            for bus_name, bus_data in buses.items():
                v = bus_data.get("voltage_pu", 1.0)
                if v < 0.90 or v > 1.10:
                    stress_points += 15.0
            collapse_probability = min(85.0, stress_points)

        # Sort propagation trajectory by time to failure
        propagation_sorted = sorted(voltage_propagation + line_propagation, key=lambda x: x[1])
        propagation_trajectory = [x[0] for x in propagation_sorted]

        return {
            "collapse_probability": round(max(0.0, min(100.0, collapse_probability)), 1),
            "survivability_horizon": round(survivability_horizon, 1),
            "predicted_overloads": predicted_overloads,
            "propagation_trajectory": propagation_trajectory
        }
