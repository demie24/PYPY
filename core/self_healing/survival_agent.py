import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.survival_agent")

class SurvivalAgent:
    """
    Responsibilities: degraded survival management, island survivability, critical infrastructure preservation,
    survivability optimization, emergency load prioritization.
    """
    def __init__(self, islanding_engine=None, guard=None):
        self.agent_name = "SurvivalAgent"
        self.confidence = 1.0

        if islanding_engine is None:
            from islanding_engine import IslandingEngine
            from topology_recovery_engine import TopologyRecoveryEngine
            self.islanding_engine = IslandingEngine(TopologyRecoveryEngine())
        else:
            self.islanding_engine = islanding_engine

        if guard is None:
            from critical_infrastructure_guard import CriticalInfrastructureGuard
            self.guard = CriticalInfrastructureGuard()
        else:
            self.guard = guard

    def evaluate(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes microgrid states, unstable zones, and critical load protection to compile proposals.
        """
        if not telemetry:
            return {"proposals": [], "confidence": 1.0}

        proposals = []
        state_data = telemetry.get("state", {})
        buses = state_data.get("buses", {})

        # Run islanding engine evaluation
        islanding_res = self.islanding_engine.analyze_islanding(telemetry, telemetry.get("attack_status"))
        active_islands = islanding_res.get("active_islands", [])
        unstable_zones = islanding_res.get("unstable_zones", [])
        splitting_commands = islanding_res.get("splitting_commands", [])

        # Propose island splitting if unstable zones exist
        for cmd in splitting_commands:
            proposals.append({
                "command": cmd["command"],
                "target": cmd["target"],
                "reason": f"SurvivalAgent: Propose emergency island splitting on {cmd['target']} to isolate unstable subgrid",
                "priority": "CRITICAL"
            })

        # Check hospital (Bus 5) status
        bus5_data = buses.get("Bus_5", {})
        bus5_v = bus5_data.get("voltage_pu", 1.0)
        
        # Calculate survival confidence
        # Lower confidence if critical Bus 5 is de-energized or voltage is very low
        if bus5_v < 0.85:
            self.confidence = 0.4
        elif unstable_zones or len(active_islands) > 1:
            self.confidence = 0.7
        else:
            self.confidence = 1.0

        return {
            "proposals": proposals,
            "confidence": self.confidence,
            "active_islands_count": len(active_islands),
            "unstable_zones": unstable_zones
        }

    def vote(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Votes on proposed grid actions.
        """
        command = proposal.get("command")
        target = proposal.get("target")

        # 1. Veto shedding critical hospital load (Bus 5)
        if command == "SHED_LOAD" and target == "Bus_5":
            logger.warning(f"[{self.agent_name}] Vetoing load shed on critical hospital {target}")
            return -1.0

        # 2. Veto opening lines that would isolate Bus 5 from all generation sources
        # We can leverage self.guard or calculate if the action disconnects Bus 5
        telemetry = context.get("telemetry")
        if telemetry and command in ["OPEN", "ISOLATE_LINE"]:
            # Check if this line is a direct source feed for Bus 5 and opening it isolates Bus 5
            # Bus 5 (index 4) has feeds L4_5 and L5_6.
            # If target is L4_5 and breakers has L5_6 OPEN, opening L4_5 will isolate Bus 5.
            breakers = telemetry.get("state", {}).get("breakers", {})
            if target == "L4_5" and breakers.get("L5_6", "CLOSED") == "OPEN":
                logger.warning(f"[{self.agent_name}] Vetoing {command} on L4_5 (would isolate critical hospital Bus 5)")
                return -1.0
            if target == "L5_6" and breakers.get("L4_5", "CLOSED") == "OPEN":
                logger.warning(f"[{self.agent_name}] Vetoing {command} on L5_6 (would isolate critical hospital Bus 5)")
                return -1.0

        # 3. Endorse emergency island splitting commands
        if command == "OPEN" and "splitting" in proposal.get("reason", "").lower():
            return 1.0

        # 4. Endorse load shedding on lower priority buses (Bus 6, Bus 8) to secure overall survivability
        if command == "SHED_LOAD" and target in ["Bus_6", "Bus_8"]:
            return 0.7

        return 0.0
