import time
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("hardware.resilience")

class DistributedResilienceManager:
    def __init__(self):
        self.survivability_score = 100.0
        self.resilience_state = "NOMINAL"  # NOMINAL, DEGRADED, CRITICAL, EMERGENCY
        self.containment_active = False
        self.escalation_level = 0  # 0 to 3
        self.alerts: List[str] = []
        
    def evaluate_resilience(self, 
                            state_manager_state: Dict[str, Any], 
                            fleet_state: Dict[str, Any], 
                            alerts_list: List[str],
                            timing_drift_detected: bool,
                            congestion_active: bool) -> Tuple[float, str]:
        """
        Fuses all degradation vectors and calculates a dynamic survivability score.
        Sets resilience states and containment controls.
        """
        self.alerts = []
        deductions = 0.0
        
        # 1. Tripped breakers deduction
        relays = state_manager_state.get("relays", {})
        open_breakers = [k for k, v in relays.items() if v.get("feedback") == "OPEN" and k != "L7_8"]
        if open_breakers:
            # 10 points deduction per tripped breaker
            penalty = len(open_breakers) * 10.0
            deductions += penalty
            self.alerts.append(f"GRID_DEGRADATION: {len(open_breakers)} tripped breaker(s) active: {', '.join(open_breakers)}")
            
        # 2. Quarantined fleet devices deduction
        fleet = fleet_state.get("fleet", {})
        quarantined = [k for k, v in fleet.items() if v.get("status") == "QUARANTINED"]
        if quarantined:
            # 15 points deduction per quarantined device
            penalty = len(quarantined) * 15.0
            deductions += penalty
            self.alerts.append(f"SECURITY_CONTAINMENT: {len(quarantined)} device(s) quarantined: {', '.join(quarantined)}")
            
        # 3. Dynamic load/overload deductions
        sensors = state_manager_state.get("sensors", {})
        overloaded_lines = []
        for key, val in sensors.items():
            if "line_" in key and "_i" in key:
                if val > 1.0:
                    overloaded_lines.append(key)
                    deductions += 15.0
        if overloaded_lines:
            self.alerts.append(f"THERMAL_OVERLOAD: {len(overloaded_lines)} line(s) overloading thermal limits: {', '.join(overloaded_lines)}")
            
        # 4. Synchronization deviations
        if timing_drift_detected:
            deductions += 10.0
            self.alerts.append("TIMING_DRIFT_WARNING: Device clock offsets exceed tolerance thresholds (>15ms)")
        if congestion_active:
            deductions += 10.0
            self.alerts.append("SYNC_CONGESTION_ALERT: Message queue load balance thresholds exceeded")
            
        # 5. Calculate final survivability score
        self.survivability_score = max(0.0, 100.0 - deductions)
        
        # 6. Establish Resilience State and Escalation Levels
        if self.survivability_score >= 90.0:
            self.resilience_state = "NOMINAL"
            self.escalation_level = 0
        elif self.survivability_score >= 70.0:
            self.resilience_state = "DEGRADED"
            self.escalation_level = 1
        elif self.survivability_score >= 40.0:
            self.resilience_state = "CRITICAL"
            self.escalation_level = 2
        else:
            self.resilience_state = "EMERGENCY"
            self.escalation_level = 3
            
        # 7. Cascading Containment Logic
        # Containment is engaged when there are overloaded lines and tripped breakers
        self.containment_active = len(overloaded_lines) > 0 and len(open_breakers) > 0
        if self.containment_active:
            self.alerts.append("CASCADING_CONTAINMENT_ACTIVE: Enforcing safety bounds to isolate line overloads.")
            
        return self.survivability_score, self.resilience_state
        
    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current resilience manager status.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "survivability_score": round(self.survivability_score, 1),
            "resilience_state": self.resilience_state,
            "containment_active": self.containment_active,
            "escalation_level": self.escalation_level,
            "alerts": self.alerts
        }
