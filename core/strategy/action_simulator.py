import logging
from typing import List, Dict, Any

logger = logging.getLogger("strategy.action_simulator")

class ActionSimulator:
    CANDIDATE_ACTIONS = [
        "ISOLATE_BUS_5",
        "QUARANTINE_LINE_L7_8",
        "LOAD_SHED_NON_CRITICAL",
        "PREEMPTIVE_REROUTE",
        "DEFENSE_ESCALATION"
    ]

    def __init__(self):
        pass

    def simulate_candidates(
        self, 
        telemetry: Dict[str, Any], 
        threat_data: Dict[str, Any], 
        alerts: List[Dict[str, Any]],
        prediction_future_risk: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate candidate defensive actions and assign risk, benefit, and stability scores.
        """
        candidates = []

        curr_threat = float(threat_data.get("threat_score", 0.0)) if threat_data else 0.0
        
        # Read risk scores from forecast
        node_risks = {}
        if prediction_future_risk:
            node_risks = prediction_future_risk.get("node_risk_scores", {})

        for action in self.CANDIDATE_ACTIONS:
            risk_score = 0.10
            benefit_score = 0.10
            stability_score = 0.90

            if action == "ISOLATE_BUS_5":
                # High cost (isolates hospital), but high benefit under active cyber threats
                risk_score = 0.75
                bus_risk = node_risks.get("Bus_5", 0.0)
                if curr_threat > 50.0 or bus_risk > 50.0:
                    benefit_score = 0.85
                    stability_score = 0.60
                else:
                    benefit_score = 0.20
                    stability_score = 0.80

            elif action == "QUARANTINE_LINE_L7_8":
                risk_score = 0.40
                if "L7_8" in telemetry.get("state", {}).get("lines", {}):
                    benefit_score = 0.30
                    stability_score = 0.85

            elif action == "LOAD_SHED_NON_CRITICAL":
                # Drops load, which has medium risk but high benefit in voltage collapses
                risk_score = 0.50
                if any(v < 0.92 for b, data in telemetry.get("state", {}).get("buses", {}).items() for v in [data.get("voltage_pu", 1.0)]):
                    benefit_score = 0.80
                    stability_score = 0.95
                else:
                    benefit_score = 0.15
                    stability_score = 0.90

            elif action == "PREEMPTIVE_REROUTE":
                # Low risk reroute action
                risk_score = 0.20
                overloaded = any(data.get("capacity_pct", 0.0) > 85.0 for l, data in telemetry.get("state", {}).get("lines", {}).items())
                if overloaded:
                    benefit_score = 0.70
                    stability_score = 0.95
                else:
                    benefit_score = 0.30
                    stability_score = 0.90

            elif action == "DEFENSE_ESCALATION":
                # Soft defense check escalation
                risk_score = 0.15
                if curr_threat > 30.0:
                    benefit_score = 0.65
                    stability_score = 0.92
                else:
                    benefit_score = 0.25
                    stability_score = 0.90

            candidates.append({
                "action": action,
                "risk_score": round(float(risk_score), 2),
                "benefit_score": round(float(benefit_score), 2),
                "stability_score": round(float(stability_score), 2)
            })

        return candidates
