import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.swarm_anomaly_fusion_engine")

class SwarmAnomalyFusionEngine:
    def __init__(self):
        self.agent_name = "SwarmAnomalyFusionEngine"
        self.status = "NOMINAL"
        self.fused_anomalies: List[Dict[str, Any]] = []
        self.swarm_threat_score = 0.0
        self.priority_queue: List[Dict[str, Any]] = []
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}

    def fuse_anomalies(
        self,
        telemetry_anoms: List[Dict[str, Any]],
        relay_anoms: List[Dict[str, Any]],
        security_alerts: List[Dict[str, Any]],
        edge_anoms: Dict[str, Any],
        simulation_mode: str = None
    ) -> Dict[str, Any]:
        """Correlates and fuses separate anomaly findings from telemetry, relay, security, and edge sources."""
        self.fused_anomalies.clear()
        self.priority_queue.clear()
        self.correlation_matrix.clear()

        # Handle simulation overrides
        if simulation_mode == "anomaly_fusion_overload":
            self.swarm_threat_score = 9.8
            self.status = "CRITICAL"
            self.fused_anomalies.append({
                "source": "FUSION_OVERLOAD",
                "severity": "CRITICAL",
                "confidence": 0.99,
                "description": "Limpahan anomali berlebihan (overload) disimulasikan di seluruh nod."
            })
            self.priority_queue = self.fused_anomalies.copy()
            self.correlation_matrix = {
                "telemetry": {"relay": 0.95, "security": 0.90, "edge": 0.85},
                "relay": {"telemetry": 0.95, "security": 0.88, "edge": 0.80},
                "security": {"telemetry": 0.90, "relay": 0.88, "edge": 0.92},
                "edge": {"telemetry": 0.85, "relay": 0.80, "security": 0.92}
            }
            return self.get_status_summary()

        # Build correlation matrix dynamically based on source activity
        active_sources = []
        if telemetry_anoms: active_sources.append("telemetry")
        if relay_anoms: active_sources.append("relay")
        if security_alerts: active_sources.append("security")
        if edge_anoms: active_sources.append("edge")

        for src1 in ["telemetry", "relay", "security", "edge"]:
            self.correlation_matrix[src1] = {}
            for src2 in ["telemetry", "relay", "security", "edge"]:
                if src1 == src2:
                    self.correlation_matrix[src1][src2] = 1.0
                elif src1 in active_sources and src2 in active_sources:
                    # high correlation if both are actively reporting anomalies
                    self.correlation_matrix[src1][src2] = 0.85
                else:
                    # baseline correlation
                    self.correlation_matrix[src1][src2] = 0.15

        # Fuse telemetry anomalies
        for anom in telemetry_anoms:
            desc = anom.get("description", "")
            self.fused_anomalies.append({
                "source": "Telemetry",
                "severity": anom.get("severity", "MEDIUM"),
                "confidence": anom.get("confidence", 0.70),
                "description": desc
            })

        # Fuse relay anomalies
        for anom in relay_anoms:
            desc = anom.get("description", "")
            self.fused_anomalies.append({
                "source": "Relay",
                "severity": anom.get("severity", "MEDIUM") if "oscillation" not in desc else "HIGH",
                "confidence": anom.get("confidence", 0.75),
                "description": f"Relay: {desc}"
            })

        # Fuse security alerts
        for alert in security_alerts:
            self.fused_anomalies.append({
                "source": "Security",
                "severity": alert.get("severity", "HIGH"),
                "confidence": alert.get("confidence", 0.80) if "confidence" in alert else 0.80,
                "description": f"Security: {alert.get('type', 'Siber')} - {alert.get('description', '')}"
            })

        # Fuse edge network anomalies
        for node_id, list_anom in edge_anoms.items():
            for anom_str in list_anom:
                self.fused_anomalies.append({
                    "source": "EdgeNetwork",
                    "severity": "CRITICAL" if anom_str == "OFFLINE" else "MEDIUM",
                    "confidence": 0.90,
                    "description": f"Node {node_id} mengalami status {anom_str}."
                })

        # Priority event queue sorting: CRITICAL > HIGH > MEDIUM > LOW
        priority_map = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
        self.priority_queue = sorted(
            self.fused_anomalies,
            key=lambda x: priority_map.get(x["severity"], 0),
            reverse=True
        )

        # Swarm threat score (0.0 to 10.0 scaling based on weighted severities)
        weighted_sum = 0.0
        for item in self.fused_anomalies:
            val = {"CRITICAL": 3.0, "HIGH": 2.0, "MEDIUM": 1.0, "LOW": 0.5}.get(item["severity"], 0.0)
            weighted_sum += val * item["confidence"]

        self.swarm_threat_score = min(10.0, weighted_sum)
        
        # Determine fusion global status
        if self.swarm_threat_score > 7.0:
            self.status = "CRITICAL"
        elif self.swarm_threat_score > 4.0:
            self.status = "HIGH"
        elif self.swarm_threat_score > 1.0:
            self.status = "DEGRADED"
        else:
            self.status = "NOMINAL"

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "fused_anomalies": self.fused_anomalies,
            "swarm_threat_score": round(self.swarm_threat_score, 2),
            "priority_queue": self.priority_queue,
            "correlation_matrix": self.correlation_matrix
        }

    def reset_engine(self):
        self.status = "NOMINAL"
        self.fused_anomalies.clear()
        self.swarm_threat_score = 0.0
        self.priority_queue.clear()
        self.correlation_matrix.clear()
