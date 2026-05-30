import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.security_agent")

class SecurityAgent:
    def __init__(self):
        self.agent_name = "SecurityAgent"
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.threat_alerts: List[Dict[str, Any]] = []
        self.safety_recommendations: List[Dict[str, Any]] = []
        self.security_logs: List[str] = []

    def analyze_security(self, threat_summary: Dict[str, Any], active_attacks: List[str]) -> Dict[str, Any]:
        """Evaluates cyber security alerts, threat scoring indexes, and active intrusion signs."""
        self.threat_alerts.clear()
        self.safety_recommendations.clear()
        self.security_logs.clear()

        # 1. Threat Interpretation & Scoring
        # threat_summary contains threat_score, severity, confidence, risk, etc.
        t_score = threat_summary.get("threat_score", 0.0)
        t_conf = threat_summary.get("confidence", 1.0)
        severity = threat_summary.get("severity", "LOW")
        self.confidence_score = float(t_conf)

        self.security_logs.append(f"Menganalisis status ancaman... Threat Index: {t_score:.1f}% ({severity})")

        # 2. Cyber-defense reasoning
        if t_score > 70.0:
            desc = f"Ancaman grid bertahap bahaya (threat score: {t_score:.1f}%)."
            self.threat_alerts.append({"type": "CYBER_THREAT_CRITICAL", "score": t_score, "description": desc, "severity": "CRITICAL"})
            self.security_logs.append("Ancaman kritikal dikesan! Melakukan penilaian sekatan.")
        elif t_score > 30.0:
            desc = f"Ancaman grid bertahap sederhana (threat score: {t_score:.1f}%)."
            self.threat_alerts.append({"type": "CYBER_THREAT_WARNING", "score": t_score, "description": desc, "severity": "HIGH"})
            self.security_logs.append("Ancaman sederhana dikesan.")

        # Handle active attacks list
        for atk in active_attacks:
            desc = f"Serangan siber '{atk}' dikesan aktif pada rangkaian grid."
            self.threat_alerts.append({"type": "ACTIVE_ATTACK", "attack": atk, "description": desc, "severity": "CRITICAL"})
            self.security_logs.append(f"Serangan aktif: {atk}")

        # 3. Security Recommendations
        # Auto-recommendations require confidence thresholds
        for alert in self.threat_alerts:
            a_type = alert["type"]
            
            if a_type == "ACTIVE_ATTACK":
                atk_name = alert["attack"]
                if self.confidence_score >= 0.75:
                    self.safety_recommendations.append({
                        "action": "QUARANTINE_NODE",
                        "target": "SCADA",
                        "suggestion": f"Serangan {atk_name} aktif. Cadangan: Kuarantin port komunikasi dan sekat arahan kawalan automatik.",
                        "severity": "CRITICAL",
                        "blocked": False
                    })
                else:
                    self.safety_recommendations.append({
                        "action": "QUARANTINE_NODE",
                        "target": "SCADA",
                        "suggestion": f"Kuarantin disekat: confidence level {self.confidence_score:.2f} rendah.",
                        "severity": "BLOCKED",
                        "blocked": True
                    })
            elif a_type == "CYBER_THREAT_CRITICAL":
                self.safety_recommendations.append({
                    "action": "OPERATOR_ESCALATION",
                    "target": "ALL",
                    "suggestion": "Amaran: Tahap ancaman kritikal. Sila tukar mod SCADA kepada kawalan manual sepenuhnya.",
                    "severity": "CRITICAL",
                    "blocked": False
                })

        # Set agent status
        if any(x["severity"] == "CRITICAL" for x in self.threat_alerts):
            self.status = "CRITICAL_ANOMALY"
        elif any(x["severity"] == "HIGH" for x in self.threat_alerts):
            self.status = "HIGH_ANOMALY"
        elif self.threat_alerts:
            self.status = "DEGRADED"
        else:
            self.status = "NOMINAL"

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "confidence_score": round(self.confidence_score, 2),
            "threat_alerts": self.threat_alerts,
            "recommendations": self.safety_recommendations,
            "security_logs": self.security_logs
        }

    def reset_agent(self):
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.threat_alerts.clear()
        self.safety_recommendations.clear()
        self.security_logs.clear()
