import os
import sys
import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.survival_forecasting")

class SurvivalForecastingEngine:
    """
    Forecasts grid survivability score over time, estimates degraded-operation duration,
    predicts recovery success probability, and simulates stabilization futures.
    """
    def __init__(self):
        pass

    def forecast_survival(self, telemetry: Dict[str, Any], predictive_stability: Dict[str, Any], proactive_active: bool) -> Dict[str, Any]:
        """
        Generates 10-step future survivability trajectories under two scenarios:
        1. "do_nothing": no proactive actions are taken, overloads/decay propagate.
        2. "mitigated": proactive rerouting/isolation/load shedding are executed.
        """
        if not telemetry:
            return {
                "do_nothing_curve": [100.0] * 10,
                "mitigated_curve": [100.0] * 10,
                "recovery_success_prob": 100.0,
                "degraded_operation_duration": 999.0
            }

        collapse_prob = predictive_stability.get("collapse_probability", 0.0)
        horizon = predictive_stability.get("survivability_horizon", 999.0)

        # Baseline current survivability score
        # Using similar logic as survival_optimizer.py
        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})

        current_score = 100.0
        # Deduct for low voltages
        v_devs = 0.0
        for b_name, b_data in buses.items():
            v = b_data.get("voltage_pu", 1.0)
            if v < 0.95 or v > 1.05:
                v_devs += abs(1.0 - v)
        current_score -= min(40.0, v_devs * 100.0)

        # Deduct for line loading
        max_load = 0.0
        for l_id, l_data in lines.items():
            cap = l_data.get("capacity_pct", 0.0)
            if cap > max_load:
                max_load = cap
        if max_load > 100.0:
            current_score -= min(40.0, (max_load - 100.0) * 2.0)
        elif max_load > 80.0:
            current_score -= (max_load - 80.0) * 0.5

        current_score = max(0.0, min(100.0, current_score))

        # Generate "Do Nothing" trajectory
        # If collapse is predicted, score decays to 0 at the horizon step
        do_nothing_curve = []
        for step in range(1, 11):
            if horizon < 999.0:
                # Decay score down based on horizon
                # e.g., if horizon is 8s, score drops to 0 at step 8
                if step * 1.0 >= horizon:
                    decayed = 0.0
                else:
                    decayed = current_score * (1.0 - (step * 1.0 / horizon))
            else:
                # If stable but stress is present
                decayed = max(0.0, current_score - step * (collapse_prob / 20.0))
            do_nothing_curve.append(round(decayed, 1))

        # Generate "Mitigated" trajectory
        # Proactive action stabilizes or restores the score back towards 95%
        mitigated_curve = []
        for step in range(1, 11):
            if proactive_active or collapse_prob > 0.0:
                # Restores voltage/loadings back to normal over 4-5 steps
                improvement = min(95.0, current_score + step * 5.0)
                # Cap drop if there is still transient decay
                val = max(current_score - 2.0, improvement)
            else:
                val = current_score
            mitigated_curve.append(round(max(0.0, min(100.0, val)), 1))

        # Recovery success probability
        # Higher if we are taking proactive actions, lower if collapse probability is extremely high
        if collapse_prob > 80.0:
            success_prob = 30.0 if not proactive_active else 75.0
        elif collapse_prob > 40.0:
            success_prob = 60.0 if not proactive_active else 88.0
        else:
            success_prob = 95.0

        # Degraded operation duration (how long can we survive in degraded mode)
        if horizon < 999.0:
            degraded_operation_duration = horizon
        else:
            degraded_operation_duration = 999.0

        return {
            "do_nothing_curve": do_nothing_curve,
            "mitigated_curve": mitigated_curve,
            "recovery_success_prob": round(success_prob, 1),
            "degraded_operation_duration": round(degraded_operation_duration, 1)
        }
