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

        # --- Phase 5B Hardening ---
        # Sequencing delay: requires N consecutive fault-detected frames before isolating
        # This prevents false trips from transient spikes.
        self.fault_detection_counter: int = 0
        self.fault_detection_delay_frames: int = 2

        # Isolation settling delay: wait N cycles in ISOLATION before attempting restoration
        # Ensures the grid state has stabilised after breaker trips before re-energising.
        self.isolation_settle_counter: int = 0
        self.isolation_settle_delay_frames: int = 3

        # Restoration cooldown: timestamp of last restoration attempt per tie-breaker
        # Prevents repeated close commands within a short window.
        self.restoration_cooldown: Dict[str, float] = {}
        self.restoration_cooldown_seconds: float = 15.0

        # Track consecutive execution calls (used to rate-limit cycle processing)
        self._cycle_counter: int = 0

    def set_mode(self, auto: bool):
        self.auto_mode = auto
        logger.info(f"FLISR Automation Mode set to: {'AUTO' if auto else 'MANUAL'}")

    def reset(self):
        self.state = "NORMAL"
        self.isolated_faults.clear()
        self.tripped_by_relay.clear()
        self.reconfigured_breakers.clear()
        self.fault_detection_counter = 0
        self.isolation_settle_counter = 0
        self.restoration_cooldown.clear()
        self._cycle_counter = 0
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

        self._cycle_counter += 1

        # FLISR State Machine execution
        if self.state == "NORMAL":
            # Idle state, monitoring
            pass

        elif self.state == "FAULT_DETECTED":
            # Phase 5B: Isolation sequencing delay — wait N frames before committing isolation
            # This prevents false trips from transient voltage spikes.
            self.fault_detection_counter += 1
            if self.fault_detection_counter < self.fault_detection_delay_frames:
                logger.debug(f"FLISR fault detection in progress ({self.fault_detection_counter}/{self.fault_detection_delay_frames} frames)...")
                return commands  # Hold — not yet committed

            # Isolation committed — register each unprocessed tripped breaker
            for tripped_bk in self.tripped_by_relay:
                if tripped_bk not in self.isolated_faults:
                    self.isolated_faults.append(tripped_bk)
                    logger.info(f"FLISR confirmed fault isolation on segment: {tripped_bk}")

            self.fault_detection_counter = 0
            self.isolation_settle_counter = 0
            self.state = "ISOLATION"
            logger.info("FLISR isolation sequence committed. Entering ISOLATION settling period...")

        elif self.state == "ISOLATION":
            # Phase 5B: Settling delay — wait N cycles before restoration to let physics converge
            self.isolation_settle_counter += 1
            if self.isolation_settle_counter < self.isolation_settle_delay_frames:
                logger.debug(f"FLISR isolation settling ({self.isolation_settle_counter}/{self.isolation_settle_delay_frames})...")
                return commands  # Hold

            self.state = "RESTORATION"
            logger.info("FLISR settling complete. Proceeding to RESTORATION...")

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

            now = time.time()
            # Find a tie-breaker that can restore power to these buses
            for tie in self.tie_breakers:
                if breakers.get(tie) == "OPEN" and tie not in self.reconfigured_breakers:
                    # Phase 5B: Restoration cooldown — prevent repeated close commands
                    last_attempt = self.restoration_cooldown.get(tie, 0.0)
                    if (now - last_attempt) < self.restoration_cooldown_seconds:
                        logger.warning(f"FLISR restoration cooldown active for {tie}. Skipping ({self.restoration_cooldown_seconds}s window).")
                        continue

                    # Verify restoration constraints (thermal limit of backup path)
                    if self._verify_restoration_safety(tie, buses):
                        self.reconfigured_breakers.append(tie)
                        self.restoration_cooldown[tie] = now  # Record attempt time
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
