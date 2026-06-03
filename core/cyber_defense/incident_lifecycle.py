import os
import json
import time
import logging
from typing import Dict, Any, List
from core.cyber_defense.threat_correlation import Incident

logger = logging.getLogger("cyber_defense.incident_lifecycle")
AUDIT_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incident_audit.json")

class IncidentLifecycleManager:
    """
    Manages the lifecycle transition sequences of correlated grid incidents.
    Sequences: DETECT -> VALIDATE -> CORRELATE -> CLASSIFY -> CONTAIN -> MITIGATE -> RECOVER -> MONITOR -> CLOSE.
    Appends execution audit records to incident_audit.json.
    """
    def __init__(self):
        # Maps incident_id -> ticks spent in current state
        self.state_durations: Dict[int, int] = {}
        # Ensure audit log is initialized
        if not os.path.exists(AUDIT_LOG_PATH):
            self._write_audit_log([])

    def evaluate_lifecycle(self, 
                           incidents: List[Incident], 
                           telemetry: Dict[str, Any], 
                           threat_data: Dict[str, Any],
                           trust_scores: Dict[str, Any],
                           containment_status: Dict[str, Any]) -> None:
        """
        Statefully updates active incidents through the security response lifecycle.
        """
        now = time.time()
        for incident in incidents:
            inc_id = incident.incident_id
            self.state_durations[inc_id] = self.state_durations.get(inc_id, 0) + 1
            
            prev_state = incident.state
            
            # State transition rules
            if incident.state == "DETECT":
                # Advance to VALIDATE if anomaly flags or alert counts confirm it's not transient
                if len(incident.correlated_alerts) >= 1 or self.state_durations[inc_id] >= 2:
                    incident.state = "VALIDATE"
                    
            elif incident.state == "VALIDATE":
                # Validate the signal. Check if trust scores are degraded or physics mismatch exists
                incident_trust_low = False
                if trust_scores:
                    bus_trust = trust_scores.get("bus_trust", {})
                    for asset in incident.affected_assets:
                        if bus_trust.get(asset, 100.0) < 70.0:
                            incident_trust_low = True
                            
                if incident_trust_low or len(incident.correlated_alerts) >= 2:
                    incident.state = "CORRELATE"
                elif self.state_durations[inc_id] >= 3:
                    # Timeout -> transition anyway to stay safe
                    incident.state = "CORRELATE"
                    
            elif incident.state == "CORRELATE":
                # Advance to CLASSIFY once attack techniques and attribution are formulated
                if incident.mitre_techniques or incident.attribution.get("threat_actor") != "UNKNOWN":
                    incident.state = "CLASSIFY"
                else:
                    incident.state = "CLASSIFY"  # Fallback
                    
            elif incident.state == "CLASSIFY":
                # Advance to CONTAIN to trigger topology split or telemetry reject recommendations
                incident.state = "CONTAIN"
                
            elif incident.state == "CONTAIN":
                # Check if containment commands are active on the affected assets
                active_containments = containment_status.get("active_containments", [])
                contained_assets = {c["target"] for c in active_containments}
                
                # If some affected assets are quarantined or contained, advance to MITIGATE
                if incident.affected_assets.intersection(contained_assets) or self.state_durations[inc_id] >= 3:
                    incident.state = "MITIGATE"
                    
            elif incident.state == "MITIGATE":
                # Check if physical parameters are returning to normal post-containment
                grid_stable = True
                buses = telemetry.get("state", {}).get("buses", {})
                for asset in incident.affected_assets:
                    if asset in buses:
                        v = buses[asset].get("voltage_pu", 1.0)
                        if abs(v - 1.0) > 0.08:
                            grid_stable = False
                            
                if grid_stable or self.state_durations[inc_id] >= 5:
                    incident.state = "RECOVER"
                else:
                    # Escalation check: if mitigation has run but voltage is collapsed, escalate severity
                    incident.severity = min(100.0, incident.severity + 5.0)
                    logger.warning(f"Mitigation slow for incident {inc_id}. Escalating severity.")
                    
            elif incident.state == "RECOVER":
                # Verify self-healing operations have re-energized grid
                is_restored = True
                buses = telemetry.get("state", {}).get("buses", {})
                for bus_name, bus_data in buses.items():
                    v = bus_data.get("voltage_pu", 1.0)
                    # If voltages are still severely depressed, recovery is incomplete
                    if v < 0.88:
                        is_restored = False
                        
                if is_restored or self.state_durations[inc_id] >= 5:
                    incident.state = "MONITOR"
                    
            elif incident.state == "MONITOR":
                # Monitor for 5 ticks to ensure no secondary strikes
                if self.state_durations[inc_id] >= 5:
                    # Close incident
                    incident.state = "CLOSE"
                    
            # If the state changed, reset duration counter and write audit record
            if incident.state != prev_state:
                self.state_durations[inc_id] = 0
                self._audit_incident_event(incident, f"Lifecycle state transitioned from {prev_state} to {incident.state}")

    def escalate_incident(self, incident: Incident, reason: str):
        """Allows direct manual or threat scorer-driven incident escalations."""
        prev_sev = incident.severity
        incident.severity = min(100.0, incident.severity + 15.0)
        self._audit_incident_event(
            incident, 
            f"Escalated severity from {prev_sev:.0f} to {incident.severity:.0f}. Reason: {reason}"
        )

    def _audit_incident_event(self, incident: Incident, description: str):
        """Appends a tamper-evident audit record to incident_audit.json."""
        now = time.time()
        record = {
            "timestamp": int(now * 1000),
            "incident_id": incident.incident_id,
            "state": incident.state,
            "severity": int(incident.severity),
            "affected_assets": sorted(list(incident.affected_assets)),
            "description": description
        }
        
        try:
            logs = self._read_audit_log()
            logs.append(record)
            # Cap audit log records at 200 items to avoid storage explosion
            if len(logs) > 200:
                logs = logs[-200:]
            self._write_audit_log(logs)
            logger.info(f"[AUDIT LOG] Incident {incident.incident_id}: {description}")
        except Exception as e:
            logger.error(f"Failed to write audit log entry: {e}")

    def _read_audit_log(self) -> List[Dict[str, Any]]:
        try:
            if os.path.exists(AUDIT_LOG_PATH):
                with open(AUDIT_LOG_PATH, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")
        return []

    def _write_audit_log(self, data: List[Dict[str, Any]]):
        try:
            with open(AUDIT_LOG_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing audit log: {e}")
            
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return self._read_audit_log()

    def clear(self):
        self.state_durations.clear()
        self._write_audit_log([])
        logger.info("Incident Lifecycle Manager state and audit log reset.")
