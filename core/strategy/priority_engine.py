import logging
from typing import List, Dict, Any

logger = logging.getLogger("strategy.priority_engine")

class PriorityEngine:
    PRIORITY_RANKS = [
        "CYBER_ATTACK",
        "VOLTAGE_COLLAPSE",
        "LINE_OVERLOAD",
        "GENERATOR_INSTABILITY",
        "RESTORATION_FAILURE"
    ]

    def __init__(self):
        pass

    def evaluate_priorities(
        self, 
        telemetry: Dict[str, Any], 
        threat_data: Dict[str, Any], 
        alerts: List[Dict[str, Any]],
        prediction_future_risk: Dict[str, Any] = None
    ) -> List[str]:
        """
        Scans grid signals to detect active and projected incidents, ranking them.
        """
        active_incidents = set()

        # 1. Cyber Attack Detection
        # Checked via active_attack flag in telemetry or high cyber threat alert
        attack_status = telemetry.get("attack_status", {})
        if attack_status.get("active_attack") or any(
            a.get("type") in ["CYBER_ATTACK", "TARGETED_FDIA", "COMPROMISE"] for a in alerts
        ):
            active_incidents.add("CYBER_ATTACK")

        # 2. Voltage Collapse Detection
        # Checked via undervoltages (<0.90 pu) or prediction metrics
        buses = telemetry.get("state", {}).get("buses", {})
        undervoltage_nodes = [
            b for b, data in buses.items() if data.get("voltage_pu", 1.0) < 0.90
        ]
        
        # Check Layer 11A future risk or forecasts
        if prediction_future_risk:
            instab_risk = prediction_future_risk.get("cyber_physical_instability_risk", {})
            future_risk_val = instab_risk.get("future_risk", 0.0)
            if future_risk_val > 70.0:
                active_incidents.add("VOLTAGE_COLLAPSE")
                
        if len(undervoltage_nodes) > 0:
            active_incidents.add("VOLTAGE_COLLAPSE")

        # 3. Line Overload Detection
        # Checked via capacity loading exceeding 100%
        lines = telemetry.get("state", {}).get("lines", {})
        overloaded_lines = [
            l for l, data in lines.items() if data.get("capacity_pct", 0.0) > 100.0
        ]
        if len(overloaded_lines) > 0 or any("OVERLOAD" in a.get("type", "") for a in alerts):
            active_incidents.add("LINE_OVERLOAD")

        # 4. Generator Instability Detection
        # Check generators (Bus_1, Bus_2, Bus_3 are generator buses in IEEE 9-bus)
        gen_buses = ["Bus_1", "Bus_2", "Bus_3"]
        for gb in gen_buses:
            if gb in buses:
                v = buses[gb].get("voltage_pu", 1.0)
                freq = buses[gb].get("frequency_hz", 60.0)
                # Significant deviation from 60 Hz or voltage bounds on gen bus
                if abs(60.0 - freq) > 2.0 or v < 0.92 or v > 1.08:
                    active_incidents.add("GENERATOR_INSTABILITY")

        # 5. Restoration Failure Detection
        # Checked via alerts or events signifying restoration failures
        if any(
            "FAILED" in a.get("event", "").upper() and "RESTORE" in a.get("event", "").upper() 
            for a in alerts
        ):
            active_incidents.add("RESTORATION_FAILURE")

        # Sort based on pre-defined severity ranking
        priority_order = [rank for rank in self.PRIORITY_RANKS if rank in active_incidents]

        # Default fallback if no urgent indicators are active
        if not priority_order:
            priority_order = ["NOMINAL_MONITORING"]

        return priority_order
