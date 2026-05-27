import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.cyber_defense_agent")

class CyberDefenseAgent:
    """
    Responsibilities: attack containment, propagation suppression, anomaly escalation, 
    cyber-defense coordination, threat prioritization.
    """
    def __init__(self):
        self.agent_name = "CyberDefenseAgent"
        self.confidence = 1.0
        self.compromised_nodes = []
        self.active_attack = None

    def evaluate(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes telemetry and cyber-defense status to formulate proposals and confidence.
        """
        if not telemetry:
            self.confidence = 1.0
            return {"proposals": [], "confidence": self.confidence}

        attack_status = telemetry.get("attack_status", {})
        self.active_attack = attack_status.get("active_attack")
        self.compromised_nodes = list(attack_status.get("compromised_nodes", {}).keys())

        # Update confidence: decays with the severity of active attacks
        if self.active_attack:
            if self.active_attack in ["coordinated_cascade", "coordinated_cyber_physical"]:
                self.confidence = 0.4
            else:
                self.confidence = 0.7
        else:
            self.confidence = 1.0

        proposals = []
        
        # 1. Propose telemetry rejection for compromised nodes
        for node in self.compromised_nodes:
            proposals.append({
                "command": "REJECT_TELEMETRY",
                "target": node,
                "reason": f"CyberDefenseAgent: Reject telemetry from compromised node {node} to avoid FDIA/spoofing propagation",
                "priority": "CRITICAL"
            })
            
            # 2. Propose breaker lockdown (OPEN and lock) for compromised nodes feeding lines
            # If a bus is compromised, we should isolate it by proposing to lockdown its breakers
            proposals.append({
                "command": "LOCKDOWN_BREAKER",
                "target": node,
                "reason": f"CyberDefenseAgent: Lockdown breakers connected to compromised {node} to contain propagation",
                "priority": "HIGH"
            })

        return {
            "proposals": proposals,
            "confidence": self.confidence,
            "active_attack": self.active_attack,
            "compromised_nodes": self.compromised_nodes
        }

    def vote(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Specialized voting on proposed actions.
        Returns:
            -1.0: Strong veto (rejection)
             0.0: Neutral
            +1.0: Endorse (approval)
        """
        command = proposal.get("command")
        target = proposal.get("target")
        source = proposal.get("source")

        # Rules:
        # 1. Veto CLOSE/RECONNECT commands on compromised lines or buses
        if command in ["CLOSE", "RECONNECT_LINE", "REROUTE_FLOW"]:
            # If the target is compromised, veto it
            if target in self.compromised_nodes:
                logger.warning(f"[{self.agent_name}] Vetoing {command} on {target} (target compromised)")
                return -1.0
            
            # If target connects to a compromised node
            # We can check topology connections (e.g. L7_8 connects to Bus 7 and Bus 8)
            # For simplicity, if Bus_7 or Bus_8 are compromised and target is L7_8 or L2_7 etc.
            for node in self.compromised_nodes:
                bus_idx = node.replace("Bus_", "")
                if bus_idx and bus_idx in target:
                    logger.warning(f"[{self.agent_name}] Vetoing {command} on {target} (connected bus {node} compromised)")
                    return -1.0

        # 2. Endorse telemetry rejection or breaker lockdowns
        if command in ["REJECT_TELEMETRY", "LOCKDOWN_BREAKER", "OPEN"]:
            if target in self.compromised_nodes:
                return 1.0

        # 3. If there is a coordinated attack and the source is not authenticated, veto
        if self.active_attack and source not in ["CYBER_DEFENSE_AGENT", "ORCHESTRATOR", "RELAY", "AGENT_CONSENSUS"]:
            logger.warning(f"[{self.agent_name}] Vetoing {command} from unauthenticated source {source} during active attack")
            return -1.0

        return 0.0
