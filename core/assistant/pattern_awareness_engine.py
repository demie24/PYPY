import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.pattern_awareness")

class PatternAwarenessEngine:
    def __init__(self):
        self.active_patterns: List[Dict[str, Any]] = []
        self.consecutive_failures: Dict[str, int] = {}
        self.voltage_oscillations_count = 0
        self.previous_voltage = 1.0

    def analyze_patterns(self, grid_state: Dict[str, Any], workflows_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.active_patterns = []

        # 1. Telemetry Pattern: Voltage Oscillation
        bus_data = grid_state.get("telemetry", {})
        curr_volt = bus_data.get("Bus_5_voltage", 1.0)
        
        # Check oscillation: large swing
        volt_delta = abs(curr_volt - self.previous_voltage)
        if volt_delta > 0.05:
            self.voltage_oscillations_count += 1
        else:
            self.voltage_oscillations_count = max(0, self.voltage_oscillations_count - 1)
            
        self.previous_voltage = curr_volt

        if self.voltage_oscillations_count >= 3:
            # Oscillation pattern detected
            conf = min(1.0, 0.5 + (self.voltage_oscillations_count - 3) * 0.1)
            self.active_patterns.append({
                "pattern_id": "voltage_oscillation_bus_5",
                "category": "TELEMETRY_ANOMALY",
                "description": "Ayunan voltan dikesan pada Bus 5 berulang kali.",
                "occurrence_count": self.voltage_oscillations_count,
                "confidence_score": round(conf, 2)
            })

        # 2. Workflow failure loops detection
        completed_wf = workflows_summary.get("completed_workflows", [])
        for wf in completed_wf:
            wf_name = wf.get("workflow_name")
            status = wf.get("status")
            if status == "FAILED":
                self.consecutive_failures[wf_name] = self.consecutive_failures.get(wf_name, 0) + 1
            elif status == "SUCCESS":
                self.consecutive_failures[wf_name] = 0

        for wf_name, count in self.consecutive_failures.items():
            if count >= 2:
                conf = min(1.0, 0.4 + count * 0.2)
                self.active_patterns.append({
                    "pattern_id": f"failure_loop_{wf_name}",
                    "category": "WORKFLOW_ANOMALY",
                    "description": f"Kegagalan berulang dikesan pada workflow '{wf_name}' ({count} kali berturut-turut).",
                    "occurrence_count": count,
                    "confidence_score": round(conf, 2)
                })

        # 3. Connection drift check
        threat_score = grid_state.get("threat", {}).get("threat_score", 0.0)
        if threat_score > 60.0 and workflows_summary.get("active_workflows_count", 0) > 2:
            self.active_patterns.append({
                "pattern_id": "high_threat_concurrency",
                "category": "ORCHESTRATION_DRIFT",
                "description": "Tindak balas workflow bertindih semasa tahap ancaman tinggi.",
                "occurrence_count": 1,
                "confidence_score": 0.65
            })

        return self.active_patterns

    def reset_counters(self) -> None:
        self.voltage_oscillations_count = 0
        self.consecutive_failures.clear()
        self.active_patterns = []

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "active_patterns_count": len(self.active_patterns),
            "active_patterns": self.active_patterns,
            "voltage_oscillations_count": self.voltage_oscillations_count,
            "consecutive_failures": self.consecutive_failures.copy()
        }
