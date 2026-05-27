import numpy as np
from typing import Dict, Any, List

class RecoveryScoringEngine:
    """
    Evaluates proposed restoration sequences and sandbox results statefully.
    Scores restoration options based on voltage stability, conductor thermal margins,
    plan execution speed, switching operations count, cascading risks, and forecast parameters.
    """
    def __init__(self):
        # Weights for the combined optimization score
        self.weights = {
            "voltage_stability": 0.15,
            "thermal_loading": 0.15,
            "restoration_speed": 0.10,
            "switching_operations": 0.10,
            "cascading_risk": 0.15,
            "rollback_probability": 0.15,
            "isolated_loads": 0.10,
            "predicted_instability": 0.10
        }

    def score_plan(self, 
                   telemetry: Dict[str, Any], 
                   sequence: List[Dict[str, Any]], 
                   sandbox_results: Dict[str, Any],
                   predicted_instability_prob: float = 0.0,
                   historical_success_rate: float = 1.0) -> Dict[str, Any]:
        """
        Computes a set of recovery metrics and a unified Recovery Optimization Score (0-100).
        """
        if not telemetry:
            return {
                "optimization_score": 0.0,
                "voltage_stability_score": 0.0,
                "thermal_loading_score": 0.0,
                "restoration_speed_score": 0.0,
                "switching_operations_score": 0.0,
                "cascading_risk_score": 0.0,
                "rollback_probability_score": 0.0,
                "isolated_load_count_score": 0.0,
                "instability_risk_score": 0.0
            }

        # 1. Voltage Stability Score
        pred_voltages = sandbox_results.get("predicted_voltages", [])
        if len(pred_voltages) > 0:
            dev = sum((v - 1.0)**2 for v in pred_voltages) / len(pred_voltages)
            voltage_score = max(0.0, min(100.0, 100.0 - 250.0 * dev))
        else:
            voltage_score = 100.0

        # 2. Thermal Loading Score
        pred_loadings = sandbox_results.get("predicted_loadings", {})
        if len(pred_loadings) > 0:
            max_load_pct = max(pred_loadings.values()) * 100.0
            if max_load_pct > 80.0:
                thermal_score = max(0.0, min(100.0, 100.0 - (max_load_pct - 80.0) * 2.5))
            else:
                thermal_score = 100.0
        else:
            thermal_score = 100.0

        # 3. Restoration Speed Score (fewer steps are better)
        steps = len(sequence)
        speed_score = max(0.0, min(100.0, 100.0 - 15.0 * max(0, steps - 1)))

        # 4. Switching Operations Score (penalize excessive commands)
        switching_score = max(0.0, min(100.0, 100.0 - 10.0 * steps))

        # 5. Cascading Risk Score (from validator sandbox)
        cascade_risk = sandbox_results.get("cascade_risk", 0.0)
        cascade_score = max(0.0, min(100.0, (1.0 - cascade_risk) * 100.0))

        # 6. Rollback Probability Score
        # Combines the current prediction risk and historical breaker failures
        rollback_prob = 0.5 * predicted_instability_prob + 0.5 * (1.0 - historical_success_rate)
        rollback_score = max(0.0, min(100.0, (1.0 - rollback_prob) * 100.0))

        # 7. Isolated Load Count Score
        # Count remaining isolated/de-energized load buses (Loads are at Bus_5, Bus_6, Bus_8)
        load_buses = [4, 5, 7]  # 0-indexed corresponding to Bus 5, 6, 8
        isolated_count = 0
        if len(pred_voltages) > 0:
            for b_idx in load_buses:
                if b_idx < len(pred_voltages):
                    if pred_voltages[b_idx] < 0.88:
                        isolated_count += 1
        isolated_score = max(0.0, min(100.0, 100.0 - 33.3 * isolated_count))

        # 8. Predicted Instability Score
        instability_score = max(0.0, min(100.0, (1.0 - predicted_instability_prob) * 100.0))

        # Calculate combined optimization score
        opt_score = (
            self.weights["voltage_stability"] * voltage_score +
            self.weights["thermal_loading"] * thermal_score +
            self.weights["restoration_speed"] * speed_score +
            self.weights["switching_operations"] * switching_score +
            self.weights["cascading_risk"] * cascade_score +
            self.weights["rollback_probability"] * rollback_score +
            self.weights["isolated_loads"] * isolated_score +
            self.weights["predicted_instability"] * instability_score
        )

        return {
            "optimization_score": float(round(opt_score, 2)),
            "voltage_stability_score": float(round(voltage_score, 2)),
            "thermal_loading_score": float(round(thermal_score, 2)),
            "restoration_speed_score": float(round(speed_score, 2)),
            "switching_operations_score": float(round(switching_score, 2)),
            "cascading_risk_score": float(round(cascade_score, 2)),
            "rollback_probability_score": float(round(rollback_score, 2)),
            "isolated_load_count_score": float(round(isolated_score, 2)),
            "instability_risk_score": float(round(instability_score, 2))
        }
