import time
import logging
import random
from typing import Dict, Any, Set, Tuple, Optional
from core.hardware.relay_controller import RelayController
from core.hardware.hardware_state_manager import HardwareStateManager

logger = logging.getLogger("hardware.virtual_relay_faults")

class VirtualRelayFaults(RelayController):
    def __init__(self, state_manager: HardwareStateManager):
        super().__init__(state_manager)
        
        # Fault Registries
        self.stuck_relays: Dict[str, str] = {}         # relay_id -> stuck state ("OPEN", "CLOSED")
        self.switching_delays: Dict[str, float] = {}   # relay_id -> delay duration (seconds)
        self.oscillating_relays: Dict[str, float] = {} # relay_id -> frequency (Hz)
        self.welded_contacts: Set[str] = set()         # relay_ids welded CLOSED
        self.desynced_relays: Set[str] = set()         # relay_ids with inverted feedback
        
        # State corruption: relay_id -> {"coil": val, "feedback": val}
        self.corrupted_states: Dict[str, Dict[str, str]] = {}

    def set_stuck_relay(self, relay_id: str, state: Optional[str]):
        if state in ["OPEN", "CLOSED"]:
            self.stuck_relays[relay_id] = state
            # Force the current state manager state to match the stuck state
            self.state_manager.update_relay_state(relay_id, state, state)
            logger.warning(f"Relay {relay_id} stuck at {state}.")
        else:
            if relay_id in self.stuck_relays:
                del self.stuck_relays[relay_id]
                logger.info(f"Relay {relay_id} unstuck.")

    def set_switching_delay(self, relay_id: str, duration: float):
        if duration > 0:
            self.switching_delays[relay_id] = duration
            logger.warning(f"Relay {relay_id} switching delay set to {duration}s.")
        else:
            if relay_id in self.switching_delays:
                del self.switching_delays[relay_id]
                logger.info(f"Relay {relay_id} switching delay cleared.")

    def set_relay_oscillation(self, relay_id: str, frequency: float):
        if frequency > 0:
            self.oscillating_relays[relay_id] = frequency
            logger.warning(f"Relay {relay_id} oscillation set to {frequency}Hz.")
        else:
            if relay_id in self.oscillating_relays:
                del self.oscillating_relays[relay_id]
                logger.info(f"Relay {relay_id} oscillation cleared.")

    def set_contact_welding(self, relay_id: str, state: bool):
        if state:
            self.welded_contacts.add(relay_id)
            # Force feedback to CLOSED immediately
            coil = self.state_manager.relays[relay_id]["coil"]
            self.state_manager.update_relay_state(relay_id, coil, "CLOSED")
            logger.warning(f"Relay {relay_id} contacts welded CLOSED.")
        else:
            self.welded_contacts.discard(relay_id)
            logger.info(f"Relay {relay_id} welding cleared.")

    def set_relay_desync(self, relay_id: str, state: bool):
        if state:
            self.desynced_relays.add(relay_id)
            # Invert feedback immediately
            coil = self.state_manager.relays[relay_id]["coil"]
            feedback = "OPEN" if coil == "CLOSED" else "CLOSED"
            self.state_manager.update_relay_state(relay_id, coil, feedback)
            logger.warning(f"Relay {relay_id} desynchronized.")
        else:
            self.desynced_relays.discard(relay_id)
            logger.info(f"Relay {relay_id} desynchronization cleared.")

    def set_relay_corruption(self, relay_id: str, coil_val: Optional[str], feedback_val: Optional[str]):
        if coil_val or feedback_val:
            self.corrupted_states[relay_id] = {
                "coil": coil_val or self.state_manager.relays[relay_id]["coil"],
                "feedback": feedback_val or self.state_manager.relays[relay_id]["feedback"]
            }
            logger.warning(f"Relay {relay_id} state corrupted: {self.corrupted_states[relay_id]}.")
        else:
            if relay_id in self.corrupted_states:
                del self.corrupted_states[relay_id]
                logger.info(f"Relay {relay_id} corruption cleared.")

    def clear_relay_faults(self):
        self.stuck_relays.clear()
        self.switching_delays.clear()
        self.oscillating_relays.clear()
        self.welded_contacts.clear()
        self.desynced_relays.clear()
        self.corrupted_states.clear()
        logger.info("All virtual relay faults cleared.")

    def trigger_switching(self, relay_id: str, target_state: str) -> Tuple[bool, str]:
        """
        Overrides trigger_switching to enforce stuck relay checks and delayed transitions.
        """
        if relay_id not in self.state_manager.relays:
            return False, f"Invalid relay identifier: {relay_id}"
            
        now = time.time()
        last_switch = self.last_switching_times.get(relay_id, 0.0)
        
        # 1. Stuck Relay Check
        if relay_id in self.stuck_relays:
            logger.warning(f"Relay switching blocked on {relay_id}: Relay is STUCK.")
            self.state_manager.decay_trust("esp32" if relay_id not in ["L6_7", "L7_8", "L8_9"] else "plc", 0.08)
            return False, f"Relay {relay_id} is stuck and cannot toggle."
            
        # 2. Anti-chattering lockout check (only if not oscillating)
        if relay_id not in self.oscillating_relays:
            if now - last_switch < self.lockout_duration:
                logger.warning(f"Relay switching blocked on {relay_id}: Anti-chattering lockout.")
                self.state_manager.decay_trust("esp32" if relay_id not in ["L6_7", "L7_8", "L8_9"] else "plc", 0.05)
                return False, f"Anti-chattering lockout active on {relay_id}."
                
        current_state = self.state_manager.relays[relay_id]["coil"]
        if current_state == target_state:
            return True, f"Relay {relay_id} already in target state {target_state}."
            
        # Register transition
        self.last_switching_times[relay_id] = now
        self.state_manager.relays[relay_id]["coil"] = target_state
        
        # Determine delay duration
        duration = self.switching_delays.get(relay_id, 0.15)
        
        self.active_transitions[relay_id] = {
            "target": target_state,
            "start_time": now,
            "duration": duration
        }
        
        logger.info(f"Relay {relay_id} coil commanded to {target_state}. Transition registered (duration={duration:.2f}s).")
        return True, f"Switching initiated on {relay_id}."

    def update_transitions(self):
        """
        Updates transitions while applying welded, desynced, oscillating, and corrupted behaviors.
        """
        now = time.time()
        completed = []
        
        # 1. Update ongoing transitions
        for rid, info in self.active_transitions.items():
            elapsed = now - info["start_time"]
            target = info["target"]
            duration = info["duration"]
            
            if elapsed >= duration:
                # Latch feedback
                if rid in self.welded_contacts:
                    self.state_manager.relays[rid]["feedback"] = "CLOSED"
                elif rid in self.desynced_relays:
                    self.state_manager.relays[rid]["feedback"] = "OPEN" if target == "CLOSED" else "CLOSED"
                else:
                    self.state_manager.relays[rid]["feedback"] = target
                completed.append(rid)
                logger.info(f"Relay {rid} transient completed.")
            else:
                # Simulate contact bouncing if normal delay
                if duration == 0.15 and elapsed > (duration - 0.05):
                    # Bouncing window
                    if rid in self.welded_contacts:
                        self.state_manager.relays[rid]["feedback"] = "CLOSED"
                    elif rid in self.desynced_relays:
                        target_inverted = "OPEN" if target == "CLOSED" else "CLOSED"
                        self.state_manager.relays[rid]["feedback"] = target_inverted if (int(elapsed * 100) % 2 == 0) else ("OPEN" if target_inverted == "CLOSED" else "CLOSED")
                    else:
                        self.state_manager.relays[rid]["feedback"] = target if (int(elapsed * 100) % 2 == 0) else ("OPEN" if target == "CLOSED" else "CLOSED")
                else:
                    # old state
                    old_state = "CLOSED" if target == "OPEN" else "OPEN"
                    if rid in self.welded_contacts:
                        self.state_manager.relays[rid]["feedback"] = "CLOSED"
                    elif rid in self.desynced_relays:
                        self.state_manager.relays[rid]["feedback"] = "CLOSED" if old_state == "CLOSED" else "OPEN"
                    else:
                        self.state_manager.relays[rid]["feedback"] = old_state

        for rid in completed:
            del self.active_transitions[rid]
            
        # 2. Process non-transitioning fault states (oscillation, corruption)
        for rid in self.state_manager.relays.keys():
            # A. Oscillation
            if rid in self.oscillating_relays:
                freq = self.oscillating_relays[rid]
                # Toggle feedback at freq Hz
                period = 1.0 / freq
                state = "CLOSED" if (int(now / period) % 2 == 0) else "OPEN"
                self.state_manager.relays[rid]["feedback"] = state
                
            # B. State corruption overrides
            if rid in self.corrupted_states:
                corr = self.corrupted_states[rid]
                self.state_manager.relays[rid]["coil"] = corr["coil"]
                self.state_manager.relays[rid]["feedback"] = corr["feedback"]

            # C. Welded contact checks (if not in transition or oscillating, force feedback)
            elif rid in self.welded_contacts and rid not in self.active_transitions and rid not in self.oscillating_relays:
                self.state_manager.relays[rid]["feedback"] = "CLOSED"

            # D. Desynced checks (if not in transition or oscillating, force feedback inverted)
            elif rid in self.desynced_relays and rid not in self.active_transitions and rid not in self.oscillating_relays:
                coil = self.state_manager.relays[rid]["coil"]
                self.state_manager.relays[rid]["feedback"] = "OPEN" if coil == "CLOSED" else "CLOSED"

            # E. Stuck checks (force state to remain stuck)
            if rid in self.stuck_relays:
                stuck_state = self.stuck_relays[rid]
                self.state_manager.relays[rid]["coil"] = stuck_state
                self.state_manager.relays[rid]["feedback"] = stuck_state

            # F. Sync GPIO feedback input pins on state manager
            pins = self.state_manager.relay_to_pins.get(rid)
            if pins:
                coil_pin = pins["coil"]
                feed_pin = pins["feedback"]
                coil_val = self.state_manager.relays[rid]["coil"]
                feed_val = self.state_manager.relays[rid]["feedback"]
                if coil_pin in self.state_manager.gpio:
                    self.state_manager.gpio[coil_pin] = 1 if coil_val == "CLOSED" else 0
                if feed_pin in self.state_manager.gpio:
                    self.state_manager.gpio[feed_pin] = 1 if feed_val == "CLOSED" else 0
