import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.relay_health")

class RelayHealthMonitor:
    def __init__(self):
        # Default list of grid breakers
        self.breakers: Dict[str, Dict[str, Any]] = {
            "L1_4": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L2_8": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L3_6": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L4_5": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L5_6": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L6_7": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L7_8": {"state": "OPEN", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L8_9": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []},
            "L4_9": {"state": "CLOSED", "switch_count": 0, "wear_pct": 0.0, "oscillation_count": 0, "unstable": False, "timing_ms": 50.0, "last_transitions": []}
        }
        
    def update_relay_state(self, breaker_id: str, state: str, timing_ms: float = 50.0):
        """Updates breaker switching state, logs timing, and analyzes wear and oscillations."""
        if breaker_id not in self.breakers:
            self.breakers[breaker_id] = {
                "state": "CLOSED",
                "switch_count": 0,
                "wear_pct": 0.0,
                "oscillation_count": 0,
                "unstable": False,
                "timing_ms": 50.0,
                "last_transitions": []
            }
            
        b = self.breakers[breaker_id]
        now = time.time()
        
        # Check transition
        if b["state"] != state:
            b["state"] = state
            b["switch_count"] += 1
            b["wear_pct"] = min(100.0, b["switch_count"] * 0.5) # 0.5% wear per transition
            b["last_transitions"].append(now)
            
        b["timing_ms"] = float(timing_ms)
        self._evaluate_oscillation(breaker_id, now)

    def _evaluate_oscillation(self, breaker_id: str, current_time: float):
        """Prunes historical transitions older than 30s and flags rapid oscillations."""
        b = self.breakers[breaker_id]
        # Keep transitions only within the last 30s
        b["last_transitions"] = [t for t in b["last_transitions"] if current_time - t <= 30.0]
        
        # More than 3 state transitions in 30s represents rapid chattering (oscillation)
        b["oscillation_count"] = len(b["last_transitions"])
        if b["oscillation_count"] >= 4:
            b["unstable"] = True
        else:
            b["unstable"] = False

    def get_recovery_recommendations(self, breaker_id: str, confidence_score: float = 1.0) -> List[Dict[str, Any]]:
        """Generates dynamic recovery workflows and suggestions in natural Malaysian Malay."""
        b = self.breakers.get(breaker_id)
        if not b:
            return []
            
        recommendations = []
        
        # Oscillation safety lockout suggestion
        if b["unstable"]:
            if confidence_score >= 0.75:
                recommendations.append({
                    "action": "LOCKOUT_BREAKER",
                    "target": breaker_id,
                    "suggestion": f"Breaker {breaker_id} sedang berayun laju (oscillation dikesan). Saya syorkan untuk lock breaker ini bagi elak kerosakan kekal.",
                    "severity": "CRITICAL"
                })
            else:
                recommendations.append({
                    "action": "LOCKOUT_BREAKER",
                    "target": breaker_id,
                    "suggestion": f"Lockout {breaker_id} disekat: confidence score ({confidence_score}) tidak mencukupi.",
                    "severity": "BLOCKED"
                })
                
        # Timing degradation suggestion
        if b["timing_ms"] > 120.0:
            if confidence_score >= 0.75:
                recommendations.append({
                    "action": "CALIBRATE_SOLENOID",
                    "target": breaker_id,
                    "suggestion": f"Breaker {breaker_id} bertindak lambat ({b['timing_ms']}ms). Saya syorkan operator jalankan solenoid timing calibration.",
                    "severity": "WARNING"
                })
                
        # High wear degradation suggestion
        if b["wear_pct"] > 80.0:
            recommendations.append({
                "action": "REPLACE_CONTACT",
                "target": breaker_id,
                "suggestion": f"Wear degradation breaker {breaker_id} dah capai {b['wear_pct']:.1f}%. Jadwalkan penukaran mechanical contact segera.",
                "severity": "HIGH"
            })
            
        return recommendations

    def get_status_summary(self) -> Dict[str, Any]:
        """Compiles health metrics, wear reports, unstable breakers, and recovery advices."""
        unstable_breakers = [k for k, v in self.breakers.items() if v["unstable"]]
        timing_anomalies = [k for k, v in self.breakers.items() if v["timing_ms"] > 120.0]
        
        wear_report = {}
        for k, v in self.breakers.items():
            if v["wear_pct"] > 50.0:
                wear_report[k] = v["wear_pct"]
                
        # Consolidate all recommendations
        all_recommendations = []
        for breaker_id in self.breakers:
            all_recommendations.extend(self.get_recovery_recommendations(breaker_id))
            
        return {
            "breakers": self.breakers,
            "unstable_breakers": unstable_breakers,
            "timing_anomalies": timing_anomalies,
            "wear_report": wear_report,
            "recommendations": all_recommendations,
            "unstable_count": len(unstable_breakers)
        }

    def reset_engine(self):
        """Wipes wear states, clears histories, and resets timing back to normal."""
        for b in self.breakers.values():
            b["switch_count"] = 0
            b["wear_pct"] = 0.0
            b["oscillation_count"] = 0
            b["unstable"] = False
            b["timing_ms"] = 50.0
            b["last_transitions"].clear()
