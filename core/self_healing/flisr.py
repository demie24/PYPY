import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("self_healing.flisr")

class FLISREngine:
    def __init__(self):
        # FLISR State Machine: NORMAL -> FAULT_DETECTED -> ISOLATION -> RESTORATION -> RESTORED
        self.state = "NORMAL"
        
        # Grid parameters
        self.tie_breakers = ["L7_8"] # Designated normally-open tie-breakers
        
        # Track faulted segments and tripped breakers
        self.isolated_faults: List[str] = []
        self.tripped_by_relay: List[str] = []
        self.reconfigured_breakers: List[str] = []
        
        # Dynamic self-healing automation switch
        self.auto_mode = True

    def set_mode(self, auto: bool):
        self.auto_mode = auto
        logger.info(f"FLISR Automation Mode set to: {'AUTO' if auto else 'MANUAL'}")

    def reset(self):
        self.state = "NORMAL"
        self.isolated_faults.clear()
        self.tripped_by_relay.clear()
        self.reconfigured_breakers.clear()
        logger.info("FLISR State Machine reset to NORMAL.")

    def process_event(self, event: Dict[str, Any]):
        """
        Listens to relay trip events to register faults.
        """
        source = event.get("source", "")
        event_text = event.get("event", "")
        
        # If event comes from a protective relay, track it
        if "Relay Trip" in event_text and "RELAY_IED_" in source:
            target_breaker = source.replace("RELAY_IED_", "")
            if target_breaker not in self.tripped_by_relay:
                self.tripped_by_relay.append(target_breaker)
                if self.state == "NORMAL":
                    self.state = "FAULT_DETECTED"
                    logger.warning(f"FLISR detected protective relay trip on {target_breaker}. Entering FAULT_DETECTED state.")

    def execute_healing_cycle(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Executes the FLISR cycle. Returns control commands to issue.
        """
        if not self.auto_mode:
            return []

        commands = []
        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        breakers = state.get("breakers", {})
        lines = state.get("lines", {})
        timestamp = telemetry.get("timestamp", int(time.time() * 1000))

        # FLISR State Machine execution
        if self.state == "NORMAL":
            # Idle state, monitoring
            pass

        elif self.state == "FAULT_DETECTED":
            # 1. Fault Location & Isolation
            # We determine which breaker tripped. Let's assume the tripped breaker isolates one side of the faulted line.
            # In distribution automation, FLISR opens downstream switches to isolate the fault.
            # If line L5_6 tripped (protection opened the breaker), we isolate the fault.
            for tripped_bk in self.tripped_by_relay:
                if tripped_bk not in self.isolated_faults:
                    self.isolated_faults.append(tripped_bk)
                    # For total isolation, we might command the other end of the line to open if it is closed.
                    # In our model, a single line status controls both ends, so it's already open.
                    logger.info(f"FLISR isolated fault on line: {tripped_bk}")
                    
            self.state = "ISOLATION"

        elif self.state == "ISOLATION":
            # Wait one sweep for state to settle, then transition to restoration
            self.state = "RESTORATION"
            logger.info("FLISR fault isolation complete. Proceeding to RESTORATION...")

        elif self.state == "RESTORATION":
            # 2. Service Restoration: Identify de-energized load buses and find backup paths
            de_energized_buses = []
            for bid, bus_data in buses.items():
                if bus_data.get("is_load", False) and bus_data.get("voltage_pu", 0.0) < 0.2:
                    de_energized_buses.append(bid)
                    
            if not de_energized_buses:
                logger.info("No de-energized buses detected. Restoration unnecessary.")
                self.state = "RESTORED"
                return []

            logger.info(f"FLISR identified de-energized load buses: {de_energized_buses}")

            # Find a tie-breaker that can restore power to these buses
            for tie in self.tie_breakers:
                if breakers.get(tie) == "OPEN" and tie not in self.reconfigured_breakers:
                    # Verify restoration constraints (thermal limit of backup path)
                    # For L7_8, it connects Bus 7 to Bus 8. 
                    # If Bus 6 is de-energized, closing L7_8 routes power from Gen 2 -> Bus 7 -> Bus 8 -> Bus 6 (via L6_7, L7_8 etc.)
                    # Let's ensure backup generator capacity is not exceeded.
                    if self._verify_restoration_safety(tie, buses):
                        self.reconfigured_breakers.append(tie)
                        commands.append({
                            "type": "RESTORATION_ACTION",
                            "command": "CLOSE",
                            "target": tie,
                            "event_log": {
                                "timestamp": timestamp,
                                "source": "FLISR_ENGINE",
                                "event": f"FLISR Self-Healing Restoration: Closed normally-open tie-breaker '{tie}' to restore power to de-energized buses: {', '.join(de_energized_buses)}",
                                "severity": "WARNING"
                            }
                        })
                        self.state = "RESTORED"
                        logger.warning(f"FLISR triggered restoration path by closing tie-breaker: {tie}")
                        break
                    else:
                        logger.error(f"FLISR cannot close tie-breaker {tie} due to backup capacity constraints.")
            
            # If no tie switch works, go directly to RESTORED state to stop looping
            if self.state == "RESTORATION":
                logger.warning("FLISR completed evaluation, no viable restoration path found.")
                self.state = "RESTORED"

        elif self.state == "RESTORED":
            # Restoration completed, wait for operator manual reset
            pass

        return commands

    def _verify_restoration_safety(self, tie_breaker: str, buses: Dict[str, Any]) -> bool:
        """
        Verify that closing this tie switch won't overload the backup generation source.
        Limit: Backup generator output must remain below 300 MW (3.0 p.u.).
        """
        if tie_breaker == "L7_8":
            # Backup generator is Gen 2 (index 1) on Bus 2
            gen2_data = buses.get("Bus_2", {})
            current_P = gen2_data.get("P_mw", 0.0)
            
            # Bus 6 load to be restored is 90 MW (0.90 p.u.)
            bus6_data = buses.get("Bus_6", {})
            load_P = bus6_data.get("P_mw", 90.0)
            
            estimated_total = current_P + load_P
            limit = 300.0 # 3.0 p.u. limit
            
            logger.info(f"FLISR Safety Check for Gen 2 capacity: Current Output: {current_P}MW, Adding load: {load_P}MW, Projected Total: {estimated_total}MW (Limit: {limit}MW)")
            return estimated_total < limit
            
        return True
