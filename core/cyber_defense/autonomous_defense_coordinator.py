import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("cyber_defense.coordinator")

class AutonomousDefenseCoordinator:
    """
    Coordinates multi-layered cyber-physical defense strategies across the grid.
    Fuses threat metrics, telemetry trust, physics estimations, and restoration policy
    to synthesize synchronous, safe containment actions.
    """
    def __init__(self):
        # Maps breaker targets to lockdown state
        self.breaker_lockdowns = {}
        # Tracks active containment strategies
        self.active_strategies = []

    def coordinate(self,
                    telemetry: Dict[str, Any],
                    threat_data: Dict[str, Any],
                    trust_scores: Dict[str, Any],
                    pinn_forecast: Dict[str, Any],
                    physics_val: Dict[str, Any],
                    escalation_level: str) -> Dict[str, Any]:
        """
        Coordinates defense actions across telemetry, topology, and restoration paths.
        """
        self.active_strategies.clear()
        actions = []
        restoration_gated = False
        lockdown_breakers = []

        # 1. Observability Preservation
        observability_degraded = False
        if pinn_forecast and pinn_forecast.get("degraded_observability", False):
            observability_degraded = True
            self.active_strategies.append("OBSERVABILITY_PRESERVATION")
            # If observability is degraded, block topology switching to avoid blind routing
            restoration_gated = True

        # 2. Restoration Lockdown
        # Lockdown automated FLISR/RL restoration in high emergency levels or when critical assets are distrusted
        critical_distrusted = False
        if trust_scores:
            bus_trust = trust_scores.get("bus_trust", {})
            if bus_trust.get("Bus_5", 100.0) < 60.0 or bus_trust.get("Bus_8", 100.0) < 60.0:
                critical_distrusted = True

        if escalation_level in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"] or critical_distrusted:
            restoration_gated = True
            self.active_strategies.append("RESTORATION_LOCKDOWN")

        # 3. Breaker Protection & Quarantine (Lock breakers targeted by attacks or in compromised/low-trust zones)
        attack_status = telemetry.get("attack_status", {})
        active_attack = attack_status.get("active_attack", False)
        compromised_nodes = attack_status.get("compromised_nodes", {})
        
        # Quarantine breakers connected to compromised buses
        for bus_name in compromised_nodes.keys():
            self.active_strategies.append("BREAKER_PROTECTION")
            connected_lines = self._get_connected_lines(bus_name)
            for line_id in connected_lines:
                lockdown_breakers.append(line_id)

        # Also quarantine breakers with very low trust (< 40%) to prevent unsafe automated switching
        if trust_scores:
            line_trust = trust_scores.get("line_trust", {})
            for line_id, score in line_trust.items():
                if score < 40.0:
                    lockdown_breakers.append(line_id)
                    self.active_strategies.append("QUARANTINE_SUSPECT_ASSETS")
                    actions.append({
                        "action": "QUARANTINE_BREAKER",
                        "target": line_id,
                        "priority": "HIGH",
                        "reason": f"Breaker trust score degraded to {score:.1f}%"
                    })

        # 4. Telemetry Isolation (Reject distrusted sensor streams)
        if trust_scores:
            bus_trust = trust_scores.get("bus_trust", {})
            line_trust = trust_scores.get("line_trust", {})
            
            for bus_name, score in bus_trust.items():
                if score < 50.0:
                    actions.append({
                        "action": "REJECT_TELEMETRY",
                        "target": bus_name,
                        "priority": "HIGH" if score < 30.0 else "MEDIUM",
                        "reason": f"Telemetry trust score degraded to {score:.1f}%"
                    })
                    
            for line_id, score in line_trust.items():
                if score < 50.0:
                    actions.append({
                        "action": "REJECT_TELEMETRY",
                        "target": line_id,
                        "priority": "HIGH" if score < 30.0 else "MEDIUM",
                        "reason": f"Line trust score degraded to {score:.1f}%"
                    })

        # 5. Topology Protection and Cascade Suppression
        lines = telemetry.get("state", {}).get("lines", {})
        breakers = telemetry.get("state", {}).get("breakers", {})
        
        # If cascade risk is high, actively isolate overloaded lines
        cascade_risk = threat_data.get("cascade_probability", 0.0) if threat_data else 0.0
        if cascade_risk > 0.40:
            self.active_strategies.append("CASCADE_SUPPRESSION")
            for line_id, line_data in lines.items():
                cap = line_data.get("capacity_pct", 0.0)
                if cap > 105.0 and breakers.get(line_id) == "CLOSED":
                    # Observability check: only isolate if we are sure of state
                    if not observability_degraded:
                        actions.append({
                            "action": "ISOLATE_LINE",
                            "target": line_id,
                            "priority": "CRITICAL",
                            "reason": f"Thermal overload cascade containment (capacity: {cap:.1f}%)"
                        })

        return {
            "strategies": list(set(self.active_strategies)),
            "recommended_defense_actions": actions,
            "restoration_lockdown_active": restoration_gated,
            "breaker_lockdown_targets": list(set(lockdown_breakers))
        }

    def _get_connected_lines(self, bus_name: str) -> List[str]:
        """Helper to get lines connected to a bus in the IEEE 9-bus grid."""
        mapping = {
            "Bus_1": ["L1_4"],
            "Bus_2": ["L2_7"],
            "Bus_3": ["L3_9"],
            "Bus_4": ["L1_4", "L4_5", "L4_9"],
            "Bus_5": ["L4_5", "L5_6"],
            "Bus_6": ["L5_6", "L6_7"],
            "Bus_7": ["L2_7", "L6_7", "L7_8"],
            "Bus_8": ["L7_8", "L8_9"],
            "Bus_9": ["L3_9", "L4_9", "L8_9"]
        }
        return mapping.get(bus_name, [])
