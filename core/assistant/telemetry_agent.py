import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.telemetry_agent")

class TelemetryAgent:
    def __init__(self):
        self.agent_name = "TelemetryAgent"
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.detected_anomalies: List[Dict[str, Any]] = []
        self.priority_events: List[Dict[str, Any]] = []
        self.cascade_alerts: List[Dict[str, Any]] = []
        self.drift_summary: Dict[str, Any] = {}
        
        # History track for cascade checks
        self.voltage_history: Dict[str, List[float]] = {}
        self.load_history: Dict[str, List[float]] = {}
        self.breaker_history: Dict[str, str] = {}

    def analyze_telemetry(self, telemetry: Dict[str, Any], sync_states: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes live telemetry and clock synchronization states to produce anomaly metrics."""
        self.detected_anomalies.clear()
        self.priority_events.clear()
        self.cascade_alerts.clear()

        # 1. Telemetry Anomaly & Confidence Scoring
        for k, v in telemetry.items():
            if not isinstance(v, (int, float)):
                continue
                
            # Bus voltage checks
            if k.startswith("bus_") and k.endswith("_v"):
                val = float(v)
                # Keep rolling voltage history
                if k not in self.voltage_history:
                    self.voltage_history[k] = []
                self.voltage_history[k].append(val)
                if len(self.voltage_history[k]) > 5:
                    self.voltage_history[k].pop(0)

                # Anomaly classification & confidence
                if val < 0.85 or val > 1.15:
                    # Very high severity deviation
                    conf = 0.95
                    severity = "CRITICAL"
                    desc = f"Voltage Bus {k.split('_')[1]} pada tahap kritikal: {val:.2f} p.u."
                    self.detected_anomalies.append({"variable": k, "value": val, "severity": severity, "confidence": conf, "description": desc})
                elif val < 0.90 or val > 1.10:
                    conf = 0.85
                    severity = "HIGH"
                    desc = f"Voltage Bus {k.split('_')[1]} di luar julat normal: {val:.2f} p.u."
                    self.detected_anomalies.append({"variable": k, "value": val, "severity": severity, "confidence": conf, "description": desc})
                elif val < 0.95 or val > 1.05:
                    conf = 0.70
                    severity = "MEDIUM"
                    desc = f"Voltage Bus {k.split('_')[1]} melencong sikit: {val:.2f} p.u."
                    self.detected_anomalies.append({"variable": k, "value": val, "severity": severity, "confidence": conf, "description": desc})

            # Line load checks
            elif k.startswith("line_") and k.endswith("_load"):
                val = float(v)
                if k not in self.load_history:
                    self.load_history[k] = []
                self.load_history[k].append(val)
                if len(self.load_history[k]) > 5:
                    self.load_history[k].pop(0)

                if val > 110.0:
                    conf = 0.98
                    severity = "CRITICAL"
                    desc = f"Line {k.split('_')[1]} mengalami beban kritikal (overload): {val:.1f}%"
                    self.detected_anomalies.append({"variable": k, "value": val, "severity": severity, "confidence": conf, "description": desc})
                elif val > 100.0:
                    conf = 0.88
                    severity = "HIGH"
                    desc = f"Line {k.split('_')[1]} melebihi kapasiti maksimum: {val:.1f}%"
                    self.detected_anomalies.append({"variable": k, "value": val, "severity": severity, "confidence": conf, "description": desc})
                elif val > 80.0:
                    conf = 0.75
                    severity = "MEDIUM"
                    desc = f"Line {k.split('_')[1]} hampir penuh: {val:.1f}%"
                    self.detected_anomalies.append({"variable": k, "value": val, "severity": severity, "confidence": conf, "description": desc})

        # 2. Telemetry Drift Reasoning
        node_drifts = sync_states.get("node_sync_states", {})
        skewed_count = 0
        max_drift_ms = 0.0
        max_drift_node = None
        
        for node_id, profile in node_drifts.items():
            drift_ms = abs(profile.get("drift_sec", 0.0)) * 1000.0
            if drift_ms > 25.0:
                skewed_count += 1
            if drift_ms > max_drift_ms:
                max_drift_ms = drift_ms
                max_drift_node = node_id
                
        # Classify drift storm state
        is_drift_storm = skewed_count >= 3
        self.drift_summary = {
            "skewed_count": skewed_count,
            "max_drift_node": max_drift_node,
            "max_drift_ms": max_drift_ms,
            "is_drift_storm": is_drift_storm,
            "description": f"Drift storm aktif (Skews: {skewed_count})" if is_drift_storm else f"Drift terkawal. Maks: {max_drift_ms:.1f}ms pada {max_drift_node}"
        }

        # 3. Telemetry Event Prioritization
        # Prioritize telemetry events by severity: CRITICAL > HIGH > MEDIUM
        self.priority_events = sorted(self.detected_anomalies, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}.get(x["severity"], 3))

        # 4. Cascading Telemetry Awareness
        # Detect if a line overload immediately followed a breaker opening
        for k, v in telemetry.items():
            if k.startswith("breaker_"):
                breaker_id = k.split("_")[1]
                state = "CLOSED" if v == 1.0 else "OPEN"
                
                # Check for state transition to OPEN
                if breaker_id in self.breaker_history and self.breaker_history[breaker_id] == "CLOSED" and state == "OPEN":
                    # Look for load spikes on other lines
                    for line_k, load_vals in self.load_history.items():
                        if len(load_vals) >= 2 and load_vals[-1] > load_vals[-2] + 15.0: # spike > 15%
                            desc = f"Cascade dikesan: Breaker {breaker_id} terpelanting (OPEN) diikuti lonjakan beban pada {line_k.split('_')[1]} ({load_vals[-1]:.1f}%)"
                            self.cascade_alerts.append({
                                "cause_breaker": breaker_id,
                                "effect_line": line_k,
                                "load_pct": load_vals[-1],
                                "description": desc
                            })
                            
                self.breaker_history[breaker_id] = state

        # Determine agent global status & overall confidence score
        if any(x["severity"] == "CRITICAL" for x in self.detected_anomalies) or is_drift_storm:
            self.status = "CRITICAL_ANOMALY"
            self.confidence_score = min(x["confidence"] for x in self.detected_anomalies) if self.detected_anomalies else 0.85
        elif any(x["severity"] == "HIGH" for x in self.detected_anomalies):
            self.status = "HIGH_ANOMALY"
            self.confidence_score = min(x["confidence"] for x in self.detected_anomalies)
        elif self.detected_anomalies:
            self.status = "DEGRADED"
            self.confidence_score = min(x["confidence"] for x in self.detected_anomalies)
        else:
            self.status = "NOMINAL"
            self.confidence_score = 1.0

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns the serialized status block of the TelemetryAgent."""
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "confidence_score": round(self.confidence_score, 2),
            "anomalies": self.detected_anomalies,
            "priority_events": self.priority_events,
            "cascade_alerts": self.cascade_alerts,
            "drift_summary": self.drift_summary
        }

    def reset_agent(self):
        """Wipes rolling telemetry history."""
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.detected_anomalies.clear()
        self.priority_events.clear()
        self.cascade_alerts.clear()
        self.drift_summary.clear()
        self.voltage_history.clear()
        self.load_history.clear()
        self.breaker_history.clear()
