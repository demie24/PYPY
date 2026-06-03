import time
import logging
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.trust_fusion")

class TrustFusionEngine:
    """
    Statefully fuses telemetry quality, physics validations, anomaly indicators,
    alert reports, and recovery histories to compute node and asset trust scores.
    """
    def __init__(self, rolling_window_size: int = 15):
        self.window_size = rolling_window_size
        
        # Telemetry history: asset -> list of historical telemetry values (to compute variance)
        self.telemetry_history: Dict[str, List[float]] = {}
        
        # Stateful trust scores: asset -> trust (0.0 to 100.0)
        self.bus_trust: Dict[str, float] = {f"Bus_{i}": 100.0 for i in range(1, 10)}
        self.line_trust: Dict[str, float] = {
            lid: 100.0 for lid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        }

    def compute_trust(self, 
                      telemetry: Dict[str, Any], 
                      alerts: List[Dict[str, Any]], 
                      physics_val: Dict[str, Any], 
                      recovery_history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fuses multi-source telemetry data to update active trust scores.
        """
        if not telemetry:
            return self.get_summary()

        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})
        
        # 1. Update Telemetry Quality (variance analysis)
        for bus_name, bus_data in buses.items():
            v = bus_data.get("voltage_pu", 1.0)
            history = self.telemetry_history.setdefault(bus_name, [])
            history.append(v)
            if len(history) > self.window_size:
                history.pop(0)
                
        # 2. Physics Validation Mismatches
        kcl_mismatches = {}
        kvl_deviations = {}
        impossible_breakers = set()
        
        if physics_val:
            # Parse KCL mismatches
            kcl_res = physics_val.get("kcl_mismatches", {})
            for b_name, val in kcl_res.items():
                kcl_mismatches[b_name] = abs(val)
                
            # Parse KVL mismatches
            kvl_res = physics_val.get("kvl_deviations", {})
            for l_id, val in kvl_res.items():
                kvl_deviations[l_id] = abs(val)
                
            # Impossible breaker states
            for violation in physics_val.get("violations", []):
                if "Impossible breaker" in violation:
                    for l_id in self.line_trust.keys():
                        if l_id in violation:
                            impossible_breakers.add(l_id)

        # 3. Active Alert Checks
        alert_counts: Dict[str, int] = {}
        for alert in alerts:
            target = alert.get("suspect_node") or alert.get("target")
            if target:
                alert_counts[target] = alert_counts.get(target, 0) + 1

        # 4. State Recovery History Penalties
        rollback_count = recovery_history.get("total_rollbacks_recorded", 0)
        failed_restorations = recovery_history.get("total_failed_restorations", 0)

        # 5. Evaluate and Decay Bus Trust
        for bus_name in self.bus_trust.keys():
            prev_trust = self.bus_trust[bus_name]
            
            # Dimension A: Telemetry Quality (high variance = unstable/tampered)
            v_history = self.telemetry_history.get(bus_name, [1.0])
            variance = np.var(v_history) if len(v_history) > 1 else 0.0
            quality_penalty = min(30.0, variance * 2000.0)  # scale variance
            
            # Dimension B: Physics Consistency (KCL MW mismatch)
            kcl_err = kcl_mismatches.get(bus_name, 0.0)
            physics_penalty = min(40.0, kcl_err * 2.0)  # scale mismatch
            
            # Dimension C: Attack Evidence (Active Alerts)
            alert_penalty = min(50.0, alert_counts.get(bus_name, 0) * 25.0)
            
            # Dimension D: Historic Failure Impacts
            history_penalty = min(20.0, rollback_count * 5.0 + failed_restorations * 10.0)
            
            # Calculate instantaneous trust
            inst_trust = 100.0 - (quality_penalty + physics_penalty + alert_penalty + history_penalty)
            inst_trust = max(0.0, min(100.0, inst_trust))
            
            # Trust score fusion with asymmetrical degradation rate (fast drop, slow recover)
            if inst_trust < prev_trust:
                # Fast degradation
                self.bus_trust[bus_name] = round(prev_trust * 0.40 + inst_trust * 0.60, 2)
            else:
                # Slow recovery
                self.bus_trust[bus_name] = round(prev_trust * 0.95 + inst_trust * 0.05, 2)

        # 6. Evaluate and Decay Line/Asset Trust
        for line_id in self.line_trust.keys():
            prev_trust = self.line_trust[line_id]
            
            # Dimension B: Physics Consistency (KVL drop deviation & impossible breaker)
            kvl_err = kvl_deviations.get(line_id, 0.0)
            physics_penalty = min(40.0, kvl_err * 200.0)
            if line_id in impossible_breakers:
                physics_penalty += 35.0
                
            # Dimension C: Attack Evidence
            alert_penalty = min(50.0, alert_counts.get(line_id, 0) * 25.0)
            
            # Calculate instantaneous trust
            inst_trust = 100.0 - (physics_penalty + alert_penalty)
            inst_trust = max(0.0, min(100.0, inst_trust))
            
            if inst_trust < prev_trust:
                self.line_trust[line_id] = round(prev_trust * 0.40 + inst_trust * 0.60, 2)
            else:
                self.line_trust[line_id] = round(prev_trust * 0.95 + inst_trust * 0.05, 2)

        return self.get_summary()

    def calculate_incident_confidence(self, alerts: List[Dict[str, Any]], physics_val: Dict[str, Any]) -> float:
        """
        Computes the probability (0.0 to 1.0) that the current incident is an active cyber attack.
        Fuses anomaly alerts with physics-aware validations to identify sensor tampering/FDIA.
        """
        if not alerts:
            return 0.0
            
        confidence = 0.30
        
        # Factor A: Alarm counts
        confidence += min(0.40, len(alerts) * 0.15)
        
        # Factor B: Severity indicators
        high_sev = any(a.get("severity") in ["CRITICAL", "HIGH"] for a in alerts)
        if high_sev:
            confidence += 0.20
            
        # Factor C: Physics impossible validations (e.g. impossible breaker)
        if physics_val and physics_val.get("physics_anomaly_score", 0.0) > 40.0:
            confidence += 0.15
            
        return round(max(0.0, min(0.99, confidence)), 2)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "bus_trust": self.bus_trust.copy(),
            "line_trust": self.line_trust.copy()
        }

    def clear(self):
        self.telemetry_history.clear()
        self.bus_trust = {f"Bus_{i}": 100.0 for i in range(1, 10)}
        self.line_trust = {
            lid: 100.0 for lid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        }
        logger.info("Trust Fusion Engine states cleared.")
