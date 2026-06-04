import logging
from typing import Dict, Any, List

logger = logging.getLogger("strategy.impact_estimator")

class ImpactEstimator:
    def __init__(self):
        pass

    def estimate_impact(
        self, 
        action: str, 
        metrics: Dict[str, float], 
        priority_order: List[str], 
        risk_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate stability gains, risk reductions, and plan execution confidence.
        """
        success_rate = metrics.get("success_rate", 1.0)
        rollback_rate = metrics.get("rollback_rate", 0.0)

        # Baseline metrics calculation
        stability_gain = 0.10
        risk_reduction = 0.10

        # Heuristic rules per candidate action type
        if action == "PREEMPTIVE_REROUTE":
            if "LINE_OVERLOAD" in priority_order:
                stability_gain = 0.35
                risk_reduction = 0.45
            else:
                stability_gain = 0.15
                risk_reduction = 0.20

        elif action == "ISOLATE_BUS_5":
            # Isolate hospital node to shield it from cyber spreads
            if "CYBER_ATTACK" in priority_order:
                stability_gain = 0.20
                risk_reduction = 0.60
            elif "VOLTAGE_COLLAPSE" in priority_order:
                stability_gain = -0.10  # Isolating hospital reduces local power stability
                risk_reduction = 0.30
            else:
                stability_gain = 0.05
                risk_reduction = 0.10

        elif action == "QUARANTINE_LINE_L7_8":
            if "CYBER_ATTACK" in priority_order or "LINE_OVERLOAD" in priority_order:
                stability_gain = 0.10
                risk_reduction = 0.35
            else:
                stability_gain = 0.05
                risk_reduction = 0.15

        elif action == "LOAD_SHED_NON_CRITICAL":
            # Reduces load to stabilize voltage, but drops overall grid performance
            if "VOLTAGE_COLLAPSE" in priority_order:
                stability_gain = 0.50
                risk_reduction = 0.40
            elif "LINE_OVERLOAD" in priority_order:
                stability_gain = 0.30
                risk_reduction = 0.35
            else:
                stability_gain = 0.10
                risk_reduction = 0.10

        elif action == "DEFENSE_ESCALATION":
            # Elevates network defense validation rules
            if "CYBER_ATTACK" in priority_order:
                stability_gain = 0.30
                risk_reduction = 0.55
            else:
                stability_gain = 0.15
                risk_reduction = 0.15

        # Incorporate historical success feedback to adjust parameters
        # High success rates boost predicted gains, while high rollback rates penalize them
        confidence = float(max(0.10, min(0.99, success_rate * (1.0 - rollback_rate))))
        
        # Apply scaling to predicted gains based on historical performance
        stability_gain = round(float(max(-0.50, min(0.99, stability_gain * (0.5 + 0.5 * success_rate)))), 2)
        risk_reduction = round(float(max(0.0, min(0.99, risk_reduction * (0.5 + 0.5 * success_rate)))), 2)

        return {
            "action": action,
            "predicted_stability_gain": stability_gain,
            "predicted_risk_reduction": risk_reduction,
            "confidence": confidence
        }
