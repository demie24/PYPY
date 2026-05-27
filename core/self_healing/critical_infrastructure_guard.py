import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("self_healing.critical_guard")

class CriticalInfrastructureGuard:
    """
    Protects critical buses and sectors. Enforces load shedding in reverse order
    of criticality (Bus 6 -> Bus 8 -> Bus 5) and intercepts unsafe shed commands.
    """
    def __init__(self):
        # Criticality priority mapping (Priority 1: highest, Priority 3: lowest)
        self.criticality = {
            "Bus_5": {"priority": 1, "name": "Control Center / Hospital Zone"},
            "Bus_8": {"priority": 2, "name": "Heavy Industrial Substation"},
            "Bus_6": {"priority": 3, "name": "Residential / Commercial Center"}
        }

    def select_load_to_shed(self, available_loads: List[str], telemetry: Dict[str, Any]) -> str:
        """
        Selects the lowest priority load that is currently energized and can be shed.
        """
        state = telemetry.get("state", {}) if telemetry else {}
        buses = state.get("buses", {})

        # Filter to loads in criticality list that are actually present
        loads_in_island = [l for l in available_loads if l in self.criticality]
        if not loads_in_island:
            return None

        # Sort by priority descending (Priority 3 first - lowest priority/first to shed)
        sorted_loads = sorted(loads_in_island, key=lambda l: self.criticality[l]["priority"], reverse=True)

        for load_bus in sorted_loads:
            # Check if this load is currently active (voltage > 0.5 pu)
            if buses.get(load_bus, {}).get("voltage_pu", 0.0) > 0.5:
                return load_bus

        return sorted_loads[0] # Fallback to first element if all offline

    def gate_load_shed_command(self, target: str, percentage: float, telemetry: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Intercepts proposed load shedding.
        Returns (approved, reason, modified_command_payload).
        Ensures we do not shed critical Bus_5 if Bus_6 or Bus_8 are still fully loadable.
        """
        if target not in self.criticality:
            return True, "Target is not a registered critical load bus", {"target": target, "percentage": percentage}

        state = telemetry.get("state", {}) if telemetry else {}
        buses = state.get("buses", {})

        target_priority = self.criticality[target]["priority"]

        # If trying to shed a high priority bus (Priority 1 or 2)
        if target_priority < 3:
            # Check if any lower priority bus (e.g. Bus_6) is still energized and has not been fully shed
            # Sort by priority descending to find the lowest priority bus first (e.g. Bus_6 priority 3, then Bus_8 priority 2)
            sorted_candidates = sorted(self.criticality.items(), key=lambda x: x[1]["priority"], reverse=True)
            for low_load, meta in sorted_candidates:
                if meta["priority"] > target_priority:
                    # Check if this lower-priority bus is energized (V > 0.5)
                    v = buses.get(low_load, {}).get("voltage_pu", 0.0)
                    if v > 0.5:
                        # Redirect shedding command to this lower-priority bus instead!
                        logger.warning(
                            f"[CRITICAL INFRASTRUCTURE GUARD] Intercepted attempt to shed critical {target}. "
                            f"Redirecting command to lower priority {low_load}."
                        )
                        return False, f"Redirected: Shielding critical infrastructure {target}. Shed {low_load} instead.", {
                            "command": "SHED_LOAD",
                            "target": low_load,
                            "percentage": percentage,
                            "source": "CRITICAL_GUARD_REDIRECTED"
                        }

        return True, "Shedding command authorized under current priority rules.", {"target": target, "percentage": percentage}
