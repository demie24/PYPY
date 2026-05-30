import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.relay_agent")

class RelayAgent:
    def __init__(self):
        self.agent_name = "RelayAgent"
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.relay_anomalies: List[Dict[str, Any]] = []
        self.stabilization_recommendations: List[Dict[str, Any]] = []
        self.coordination_support_needed: List[str] = []

    def analyze_relays(self, relay_health_summary: Dict[str, Any], global_confidence: float = 1.0) -> Dict[str, Any]:
        """Analyzes physical relay states and wear statistics, providing safety recommendations."""
        self.relay_anomalies.clear()
        self.stabilization_recommendations.clear()
        self.coordination_support_needed.clear()
        self.confidence_score = float(global_confidence)

        breakers = relay_health_summary.get("breakers", {})
        unstable_breakers = relay_health_summary.get("unstable_breakers", [])
        timing_anomalies = relay_health_summary.get("timing_anomalies", [])
        wear_report = relay_health_summary.get("wear_report", {})

        # 1. Anomaly Interpretation
        for bk, profile in breakers.items():
            wear = profile.get("wear_pct", 0.0)
            timing = profile.get("timing_ms", 50.0)
            unstable = profile.get("unstable", False)
            
            if unstable:
                desc = f"Breaker {bk} mengalami chattering (oscillating). Sangat tidak stabil!"
                self.relay_anomalies.append({"breaker": bk, "metric": "OSCILLATION", "value": wear, "description": desc, "severity": "CRITICAL"})
            if wear > 80.0:
                desc = f"Breaker {bk} haus (wear) kritikal pada {wear:.1f}%."
                self.relay_anomalies.append({"breaker": bk, "metric": "WEAR", "value": wear, "description": desc, "severity": "HIGH"})
            elif wear > 50.0:
                desc = f"Breaker {bk} haus (wear) sederhana pada {wear:.1f}%."
                self.relay_anomalies.append({"breaker": bk, "metric": "WEAR", "value": wear, "description": desc, "severity": "MEDIUM"})
            if timing > 120.0:
                desc = f"Breaker {bk} bertindak lambat (latency) pada {timing:.1f}ms."
                self.relay_anomalies.append({"breaker": bk, "metric": "TIMING", "value": timing, "description": desc, "severity": "HIGH"})

        # 2. Stabilization Recommendations
        for anomaly in self.relay_anomalies:
            bk = anomaly["breaker"]
            metric = anomaly["metric"]
            severity = anomaly["severity"]
            
            if metric == "OSCILLATION":
                if self.confidence_score >= 0.75:
                    self.stabilization_recommendations.append({
                        "action": "LOCKOUT_BREAKER",
                        "target": bk,
                        "suggestion": f"Sila buat lockout keselamatan segera pada breaker {bk} bagi mengelakkan kerosakan fizikal (oscillation dikesan).",
                        "severity": "CRITICAL",
                        "blocked": False
                    })
                    self.coordination_support_needed.append(f"Execute lockout safety-sequence on {bk}")
                else:
                    self.stabilization_recommendations.append({
                        "action": "LOCKOUT_BREAKER",
                        "target": bk,
                        "suggestion": f"LOCKOUT {bk} disekat: confidence level {self.confidence_score:.2f} di bawah paras threshold 0.75.",
                        "severity": "BLOCKED",
                        "blocked": True
                    })
            elif metric == "TIMING":
                if self.confidence_score >= 0.75:
                    self.stabilization_recommendations.append({
                        "action": "CALIBRATE_SOLENOID",
                        "target": bk,
                        "suggestion": f"Breaker {bk} dikesan bertindak perlahan ({anomaly['value']:.1f}ms). Operator disyorkan jalankan solenoid timing calibration.",
                        "severity": "HIGH",
                        "blocked": False
                    })
                    self.coordination_support_needed.append(f"Solenoid calibration workflow on {bk}")
            elif metric == "WEAR" and severity == "HIGH":
                self.stabilization_recommendations.append({
                    "action": "REPLACE_CONTACT",
                    "target": bk,
                    "suggestion": f"Breaker {bk} dah haus sebanyak {anomaly['value']:.1f}%. Sila buat mechanical maintenance untuk ganti physical contact.",
                    "severity": "HIGH",
                    "blocked": False
                })

        # Set agent state based on findings
        if any(x["severity"] == "CRITICAL" for x in self.relay_anomalies):
            self.status = "CRITICAL_ANOMALY"
        elif any(x["severity"] == "HIGH" for x in self.relay_anomalies):
            self.status = "HIGH_ANOMALY"
        elif self.relay_anomalies:
            self.status = "DEGRADED"
        else:
            self.status = "NOMINAL"

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "confidence_score": round(self.confidence_score, 2),
            "anomalies": self.relay_anomalies,
            "recommendations": self.stabilization_recommendations,
            "coordination_support_needed": self.coordination_support_needed
        }

    def reset_agent(self):
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.relay_anomalies.clear()
        self.stabilization_recommendations.clear()
        self.coordination_support_needed.clear()
