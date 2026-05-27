import os
import sys
import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.self_preservation_policy")

class SelfPreservationPolicyEngine:
    """
    Implements AI survival policies prioritizing grid longevity over aggressive restoration,
    dynamically switching stabilization strategies and executing graceful degradation load shedding.
    """
    def __init__(self):
        self.active_policy = "NOMINAL" # NOMINAL, PREVENTATIVE, SELF_PRESERVATION, EMERGENCY_DEGRADATION
        self.proactive_shed_history = set()

    def evaluate_policy(self, telemetry: Dict[str, Any], predictive_stability: Dict[str, Any]) -> Dict[str, Any]:
        """
        Switches survival policies statefully and issues preemptive load shedding.
        """
        if not telemetry:
            return {
                "active_policy": "NOMINAL",
                "preservation_rules": [],
                "proactive_commands": []
            }

        collapse_prob = predictive_stability.get("collapse_probability", 0.0)
        horizon = predictive_stability.get("survivability_horizon", 999.0)

        # Transition policy states
        if collapse_prob >= 75.0 or horizon < 10.0:
            self.active_policy = "EMERGENCY_DEGRADATION"
        elif collapse_prob >= 40.0 or horizon < 30.0:
            self.active_policy = "SELF_PRESERVATION"
        elif collapse_prob >= 15.0 or horizon < 60.0:
            self.active_policy = "PREVENTATIVE"
        else:
            self.active_policy = "NOMINAL"

        preservation_rules = []
        proactive_commands = []

        state = telemetry.get("state", {})
        buses = state.get("buses", {})

        # Define preservation rules and actions based on policy
        if self.active_policy == "NOMINAL":
            preservation_rules.append("Longevity Priority: Nominal operations. Suppress overrides.")
        
        elif self.active_policy == "PREVENTATIVE":
            preservation_rules.append("Pre-failure topology adaptation active. Block risky reclosing.")
            # Block restoration if a line is close to overloading
            preservation_rules.append("Restoration cooldowns extended by 5s.")

        elif self.active_policy == "SELF_PRESERVATION":
            preservation_rules.append("Shed non-critical load (Bus 6) proactively to prevent frequency decay.")
            preservation_rules.append("Prioritize generator online status over voltage limits.")
            
            # Shed Bus 6 load (lowest priority) if not already fully shed
            bus_6_data = buses.get("Bus_6", {})
            bus_6_p = bus_6_data.get("P_mw", 0.0)
            if bus_6_p > 10.0 and "Bus_6" not in self.proactive_shed_history:
                proactive_commands.append({
                    "command": "SHED_LOAD",
                    "target": "Bus_6",
                    "percentage": 25.0,
                    "reason": f"Self Preservation: Pre-emptive shedding of non-critical Bus 6 to avoid cascade (Collapse Risk: {collapse_prob}%)"
                })
                self.proactive_shed_history.add("Bus_6")

        elif self.active_policy == "EMERGENCY_DEGRADATION":
            preservation_rules.append("CRITICAL: Grid longevity prioritized. Shed Bus 6 and Bus 8 loads.")
            preservation_rules.append("Strict reclosing lock: Zero restoration permitted.")
            
            # Shed Bus 6 (if not done) and Bus 8
            for bus_name in ["Bus_6", "Bus_8"]:
                bus_data = buses.get(bus_name, {})
                bus_p = bus_data.get("P_mw", 0.0)
                if bus_p > 10.0 and bus_name not in self.proactive_shed_history:
                    proactive_commands.append({
                        "command": "SHED_LOAD",
                        "target": bus_name,
                        "percentage": 30.0,
                        "reason": f"Emergency Preservation: Pre-emptive load shedding on {bus_name} to stabilize frequency (Horizon: {horizon}s)"
                    })
                    self.proactive_shed_history.add(bus_name)

        # Clear history if system goes back to NOMINAL
        if self.active_policy == "NOMINAL":
            self.proactive_shed_history.clear()

        return {
            "active_policy": self.active_policy,
            "preservation_rules": preservation_rules,
            "proactive_commands": proactive_commands
        }
