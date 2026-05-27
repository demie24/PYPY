import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.prediction_agent")

class PredictionAgent:
    """
    Responsibilities: collapse forecasting, survivability prediction, instability trajectory prediction,
    restoration confidence forecasting, future-risk estimation.
    """
    def __init__(self, predictive_engine=None, forecast_engine=None):
        self.agent_name = "PredictionAgent"
        self.confidence = 1.0

        if predictive_engine is None:
            from predictive_stability_engine import PredictiveStabilityEngine
            self.predictive_engine = PredictiveStabilityEngine()
        else:
            self.predictive_engine = predictive_engine

        if forecast_engine is None:
            from survival_forecasting_engine import SurvivalForecastingEngine
            self.forecast_engine = SurvivalForecastingEngine()
        else:
            self.forecast_engine = forecast_engine

    def evaluate(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes 10-step forecasts, collapse horizons, and prediction confidence to compile proposals.
        """
        if not telemetry:
            return {"proposals": [], "confidence": 1.0}

        proposals = []

        # Run predictive stability evaluation
        pred_stability_res = self.predictive_engine.evaluate_predictive_stability(telemetry)
        collapse_prob = pred_stability_res.get("collapse_probability", 0.0)
        horizon = pred_stability_res.get("survivability_horizon", 999.0)
        predicted_overloads = pred_stability_res.get("predicted_overloads", [])

        # Run survival forecast evaluation
        forecast_res = self.forecast_engine.forecast_survival(
            telemetry, pred_stability_res, len(predicted_overloads) > 0
        )
        success_prob = forecast_res.get("recovery_success_prob", 100.0)

        # Update confidence: scales with ML prediction confidence if available, else nominal
        # Extracted from telemetry.get("ai_prediction", {}).get("confidence", 0.90)
        ai_pred = telemetry.get("ai_prediction", {})
        if isinstance(ai_pred, dict) and "confidence" in ai_pred:
            self.confidence = ai_pred["confidence"]
        else:
            self.confidence = 0.95

        # 1. Propose preemptive isolation if an overload is predicted to trip soon
        for overload in predicted_overloads:
            trip_time = overload.get("predicted_time_to_trip", 999.0)
            if trip_time < 15.0:
                proposals.append({
                    "command": "OPEN", # Preemptive isolation
                    "target": overload["line_id"],
                    "reason": f"PredictionAgent: Propose preemptive isolation on line {overload['line_id']} due to predicted trip in {trip_time:.1f}s",
                    "priority": "CRITICAL" if trip_time < 5.0 else "HIGH"
                })

        # 2. Propose proactive load shedding if collapse probability is extremely high
        if collapse_prob > 50.0:
            # Recommend shedding non-critical load (Bus 6)
            proposals.append({
                "command": "SHED_LOAD",
                "target": "Bus_6",
                "percentage": 25.0,
                "reason": f"PredictionAgent: Proposing proactive load shed on Bus 6 to prevent voltage collapse (Collapse Probability: {collapse_prob}%)",
                "priority": "HIGH"
            })

        return {
            "proposals": proposals,
            "confidence": self.confidence,
            "collapse_probability": collapse_prob,
            "survivability_horizon": horizon,
            "success_probability": success_prob
        }

    def vote(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Votes on proposed grid actions.
        """
        command = proposal.get("command")
        target = proposal.get("target")

        # Context holds stability/forecast data
        collapse_probability = context.get("collapse_probability", 0.0)
        success_probability = context.get("success_probability", 100.0)

        # 1. Endorse actions that resolve predicted overloads
        # If target matches one of the predicted overload lines and command is OPEN (preemptive isolation)
        predicted_overloads = context.get("predicted_overloads", [])
        for overload in predicted_overloads:
            if overload["line_id"] == target and command == "OPEN":
                return 1.0

        # 2. Endorse load shedding if collapse is predicted
        if command == "SHED_LOAD" and collapse_probability > 40.0:
            return 0.8

        # 3. Veto proposed closing actions if the success probability is low (<40%)
        if command in ["CLOSE", "RECONNECT_LINE", "REROUTE_FLOW"] and success_probability < 40.0:
            logger.warning(f"[{self.agent_name}] Vetoing {command} on {target} (low success probability: {success_probability:.1f}%)")
            return -1.0

        return 0.0
