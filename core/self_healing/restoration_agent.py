import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.restoration_agent")

class RestorationAgent:
    """
    Responsibilities: restoration sequencing, blackstart coordination, rollback handling,
    recovery optimization, topology restoration.
    """
    def __init__(self, fsm=None, memory=None):
        self.agent_name = "RestorationAgent"
        self.confidence = 1.0
        
        # Fallback inline objects if not provided
        if fsm is None:
            from recovery_state_machine import RecoveryStateMachine
            self.fsm = RecoveryStateMachine()
        else:
            self.fsm = fsm

        if memory is None:
            from adaptive_recovery_memory import AdaptiveRecoveryMemory
            self.memory = AdaptiveRecoveryMemory()
        else:
            self.memory = memory

    def evaluate(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes FSM state, active outages, and historical memory to compile proposals.
        """
        if not telemetry:
            return {"proposals": [], "confidence": 1.0}

        proposals = []
        state_data = telemetry.get("state", {})
        breakers = state_data.get("breakers", {})
        buses = state_data.get("buses", {})

        # Determine if grid is collapsed (e.g. all generator voltages near zero)
        collapsed = True
        for b_name, b_data in buses.items():
            if b_data.get("is_gen", False) and b_data.get("voltage_pu", 1.0) > 0.3:
                collapsed = False
                break

        # 1. Propose blackstart initialization if grid is collapsed and not already in blackstart
        if collapsed:
            self.confidence = 0.5
            proposals.append({
                "command": "INITIATE_BLACKSTART",
                "target": "SYSTEM",
                "reason": "RestorationAgent: Complete grid collapse detected. Proposing blackstart restoration.",
                "priority": "CRITICAL"
            })
            return {
                "proposals": proposals, 
                "confidence": self.confidence,
                "fsm_state": self.fsm.state,
                "collapsed": collapsed
            }

        # 2. Check if restoration FSM needs to trigger or has a planned sequence
        # We can suggest closing/opening lines based on the FSM planned sequence
        if self.fsm.planned_sequence:
            for step in self.fsm.planned_sequence:
                # Use laplace success score as basis for step priority
                hist_conf = self.memory.get_sequence_confidence([step])
                proposals.append({
                    "command": step["command"],
                    "target": step["target"],
                    "reason": f"RestorationAgent: Proposing step {step['command']} on {step['target']} (FSM state: {self.fsm.state}, confidence: {hist_conf:.2f})",
                    "priority": "HIGH" if hist_conf > 0.7 else "MEDIUM"
                })

        # Calculate agent confidence: higher if FSM is normal/restored, lower if in rollback/isolate
        if self.fsm.state == "NORMAL":
            self.confidence = 1.0
        elif self.fsm.state in ["ISOLATE", "REROUTE"]:
            self.confidence = 0.8
        elif self.fsm.state == "RESTORE":
            self.confidence = 0.9
        elif self.fsm.state == "ROLLBACK":
            self.confidence = 0.3
        else:
            self.confidence = 0.6

        return {
            "proposals": proposals,
            "confidence": self.confidence,
            "fsm_state": self.fsm.state,
            "collapsed": collapsed
        }

    def vote(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Votes on proposed grid actions.
        """
        command = proposal.get("command")
        target = proposal.get("target")

        # 1. Rejects CLOSE commands on locked-out breakers
        if command in ["CLOSE", "RECONNECT_LINE", "REROUTE_FLOW"]:
            if self.fsm.rollback_guard.is_locked_out(target):
                logger.warning(f"[{self.agent_name}] Vetoing {command} on {target} (breaker locked out)")
                return -1.0
            
            # Rejects restoration CLOSE commands if grid is collapsed (requires blackstart first)
            collapsed_context = context.get("collapsed", False)
            if collapsed_context and command != "INITIATE_BLACKSTART":
                logger.warning(f"[{self.agent_name}] Vetoing restoration command {command} on {target} (grid collapsed, blackstart needed)")
                return -1.0

        # 2. Endorse proposed FSM steps
        if self.fsm.planned_sequence:
            for step in self.fsm.planned_sequence:
                if step["command"] == command and step["target"] == target:
                    hist_conf = self.memory.get_sequence_confidence([step])
                    # Higher endorsement if memory shows high success rate
                    return 0.5 + 0.5 * hist_conf

        # 3. Endorse blackstart steps
        if command == "INITIATE_BLACKSTART":
            return 1.0

        return 0.0
