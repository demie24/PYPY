import time
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("hardware.relay_controller")

class RelayController:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        
        # Lockout times to prevent anti-chattering (damage prevention)
        self.last_switching_times = {rid: 0.0 for rid in self.state_manager.relays.keys()}
        self.lockout_duration = 2.0  # seconds between switches
        
        # Ongoing transition tracks
        # {relay_id: (target_state, start_time, duration)}
        self.active_transitions = {}
        
    def trigger_switching(self, relay_id: str, target_state: str) -> Tuple[bool, str]:
        """
        Commands a relay to toggle (OPEN/CLOSED).
        Validates anti-chattering lockouts before proceeding.
        """
        if relay_id not in self.state_manager.relays:
            return False, f"Invalid relay identifier: {relay_id}"
            
        now = time.time()
        last_switch = self.last_switching_times[relay_id]
        
        # 1. Anti-chattering Lockout Check
        if now - last_switch < self.lockout_duration:
            logger.warning(f"Relay switching blocked on {relay_id}: Anti-chattering lockout (elapsed: {now - last_switch:.2f}s).")
            # Penalize trust
            self.state_manager.decay_trust("esp32", 0.05)
            self.state_manager.decay_trust("plc", 0.05)
            return False, f"Anti-chattering lockout active. Switch blocked on {relay_id}."
            
        current_state = self.state_manager.relays[relay_id]["coil"]
        if current_state == target_state:
            return True, f"Relay {relay_id} already in target state {target_state}."
            
        # Register transition
        self.last_switching_times[relay_id] = now
        # Coil changes immediately (electrical control signal latch)
        self.state_manager.relays[relay_id]["coil"] = target_state
        
        # Auxiliary contact feedback lags (physical motion)
        # Transition duration: 150ms delay
        self.active_transitions[relay_id] = {
            "target": target_state,
            "start_time": now,
            "duration": 0.15
        }
        
        logger.info(f"Relay {relay_id} coil commanded to {target_state}. Contact transition started.")
        return True, f"Switching initiated on {relay_id}."
        
    def update_transitions(self):
        """
        Updates the physical contacts state machine.
        Should be called in the execution daemon loop.
        """
        now = time.time()
        completed = []
        
        for rid, info in self.active_transitions.items():
            elapsed = now - info["start_time"]
            target = info["target"]
            duration = info["duration"]
            
            # During transition (0ms to 150ms):
            # Model contact bounce. 100ms delay + 50ms bounce
            if elapsed >= duration:
                # Latch feedback fully
                self.state_manager.relays[rid]["feedback"] = target
                completed.append(rid)
                logger.info(f"Relay {rid} contacts fully latched to {target} (transient completed).")
            else:
                # Simulate contact bouncing (intermittent OPEN/CLOSED state reads)
                # If we are in the bounce window (last 50ms of transition), random fluctuations
                if elapsed > (duration - 0.05):
                    bouncing_feedback = target if (int(elapsed * 100) % 2 == 0) else ("OPEN" if target == "CLOSED" else "CLOSED")
                    self.state_manager.relays[rid]["feedback"] = bouncing_feedback
                else:
                    # Stays at old state
                    self.state_manager.relays[rid]["feedback"] = "CLOSED" if target == "OPEN" else "OPEN"
                    
        for rid in completed:
            del self.active_transitions[rid]
            
    def get_relay_telemetry(self) -> Dict[str, Any]:
        return {
            "timestamp": int(time.time() * 1000),
            "relays": {rid: data.copy() for rid, data in self.state_manager.relays.items()}
        }
