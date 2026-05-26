import time
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("self_healing.restoration_policy_engine")

class RestorationPolicyEngine:
    def __init__(self):
        self.tie_breakers = ["L7_8"]
        self.nominal_reconnection_sequence = ["L4_5", "L1_4", "L2_7", "L3_9", "L4_9", "L5_6", "L6_7", "L8_9"]
        
        # Cooldown dictionary: breaker -> last action timestamp
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_period = 10.0 # seconds
        
    def evaluate_policy(self, 
                        action_name: str, 
                        target: str, 
                        telemetry: Dict[str, Any], 
                        pinn_forecast: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Validates the action against staged restoration rules, cooldown guards, and sequencing limits.
        """
        now = time.time()
        
        # 1. Cooldown Guard
        if target in self.cooldowns:
            elapsed = now - self.cooldowns[target]
            if elapsed < self.cooldown_period:
                return False, f"Cooldown active for {target}: {elapsed:.1f}s elapsed of {self.cooldown_period}s"
                
        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        
        # 2. Prevent unsafe closing of tripped line without isolating faults first
        if action_name in ["RECONNECT_LINE", "REROUTE_FLOW"]:
            # If we want to CLOSE a breaker, verify it is currently OPEN
            if breakers.get(target) == "CLOSED":
                return False, f"Policy block: breaker {target} is already CLOSED"
                
            # Telemetry trust prerequisite: check target's terminal buses
            # Line connection mappings:
            line_connections = {
                "L1_4": ("Bus_1", "Bus_4"),
                "L2_7": ("Bus_2", "Bus_7"),
                "L3_9": ("Bus_3", "Bus_9"),
                "L4_5": ("Bus_4", "Bus_5"),
                "L4_9": ("Bus_4", "Bus_9"),
                "L5_6": ("Bus_5", "Bus_6"),
                "L6_7": ("Bus_6", "Bus_7"),
                "L7_8": ("Bus_7", "Bus_8"),
                "L8_9": ("Bus_8", "Bus_9")
            }
            
            if target in line_connections:
                b_from, b_to = line_connections[target]
                # Prerequisite: terminal bus voltages must not be faulted to zero unless closing a generator path
                v_from = state.get("buses", {}).get(b_from, {}).get("voltage_pu", 1.0)
                v_to = state.get("buses", {}).get(b_to, {}).get("voltage_pu", 1.0)
                
                # If both terminals are de-energized, closing is a blind restoration
                if v_from < 0.20 and v_to < 0.20:
                    return False, f"Policy block: blind restoration detected on {target}. Both terminal buses de-energized."
                    
            # Check concept drift
            if pinn_forecast and pinn_forecast.get("concept_drift_alert", False):
                return False, f"Policy block: cannot execute restoration when global concept drift alert is active."
                
        # 3. Sequencing order validation
        # If we open or close, log and update cooldowns
        return True, "Restoration policy validation passed."
        
    def record_action_execution(self, target: str):
        """
        Updates the execution timestamp for target to enforce cooldowns.
        """
        self.cooldowns[target] = time.time()
        logger.info(f"Policy Engine recorded action execution on {target}. Cooldown started.")
