import time
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("hardware.safety_guard")

class SafeRelayGuard:
    def __init__(self):
        self.emergency_stop_active = False
        self.alerts: List[str] = []
        
        # Default Safe States Registry
        self.default_safe_states = {
            "L1_4": "CLOSED",
            "L2_7": "CLOSED",
            "L3_9": "CLOSED",
            "L4_5": "CLOSED",
            "L4_9": "CLOSED",
            "L5_6": "CLOSED",
            "L6_7": "CLOSED",
            "L7_8": "OPEN",
            "L8_9": "CLOSED"
        }
        
        # Line connected buses mappings
        self.line_to_buses = {
            "L1_4": (1, 4),
            "L2_7": (2, 7),
            "L3_9": (3, 9),
            "L4_5": (4, 5),
            "L4_9": (4, 9),
            "L5_6": (5, 6),
            "L6_7": (6, 7),
            "L7_8": (7, 8),
            "L8_9": (8, 9)
        }

    def trigger_emergency_stop(self) -> List[Dict[str, Any]]:
        """
        Triggers emergency stop, locking command execution and generating
        commands to trip/latch all relays to their default safe states.
        """
        self.emergency_stop_active = True
        alert_msg = "EMERGENCY_STOP_TRIGGERED: All controls locked. Forcing safe default states."
        if alert_msg not in self.alerts:
            self.alerts.append(alert_msg)
        logger.critical(alert_msg)
        
        commands = []
        for relay_id, safe_state in self.default_safe_states.items():
            commands.append({
                "command": safe_state,
                "target": relay_id,
                "source": "SAFETY_GUARD"
            })
        return commands

    def reset_emergency_stop(self):
        """
        Resets emergency stop and unlocks command execution.
        """
        self.emergency_stop_active = False
        alert_msg = "EMERGENCY_STOP_RESET: Controls unlocked."
        self.alerts.append(alert_msg)
        logger.info(alert_msg)

    def validate_command(self, command: Dict[str, Any], current_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates command safety against E-stop status, generator isolation,
        parallel synchronism, and anti-cascade thermal load limits.
        """
        if self.emergency_stop_active:
            return False, "BLOCKED: Emergency Stop is active. All control actions are locked out."
            
        cmd_type = command.get("command")
        target = command.get("target")
        
        # Non-switching commands bypass relay safety checks
        if cmd_type not in ["OPEN", "CLOSE", "CLOSED"]:
            return True, "Bypassed: Non-switching command."
            
        if target not in self.default_safe_states:
            return False, f"BLOCKED: Unknown breaker target: {target}."
            
        sensors = current_state.get("sensors", {})
        
        # 1. Generator Isolation Avoidance (radial connections)
        # L1_4, L2_7, L3_9 are radial lines to Generators. Opening them isolates the generator.
        if cmd_type == "OPEN" and target in ["L1_4", "L2_7", "L3_9"]:
            alert_msg = f"INTERLOCK_VIOLATION: Opening {target} would isolate generator at Bus {self.line_to_buses[target][0]}."
            self.alerts.append(alert_msg)
            logger.warning(alert_msg)
            return False, alert_msg

        # 2. Parallel Check Syncs (Closing breakers)
        # Block closing if voltage difference between the terminal buses exceeds 0.1 pu.
        if cmd_type in ["CLOSE", "CLOSED"] and target in self.line_to_buses:
            bus_from, bus_to = self.line_to_buses[target]
            v_from = sensors.get(f"bus_{bus_from}_v", 1.0)
            v_to = sensors.get(f"bus_{bus_to}_v", 1.0)
            
            if abs(v_from - v_to) > 0.1:
                alert_msg = f"PARALLEL_SYNC_FAIL: Voltage delta across {target} is {abs(v_from - v_to):.3f} pu (>0.1 pu limit)."
                self.alerts.append(alert_msg)
                logger.warning(alert_msg)
                return False, alert_msg

        # 3. Anti-Cascade protection (Opening breakers)
        # Check if adjacent lines (sharing a terminal bus) have currents exceeding 95% limit (0.95 pu).
        if cmd_type == "OPEN" and target in self.line_to_buses:
            bus_from, bus_to = self.line_to_buses[target]
            
            # Find adjacent lines
            adjacent_lines = []
            for line, buses in self.line_to_buses.items():
                if line != target:
                    if bus_from in buses or bus_to in buses:
                        adjacent_lines.append(line)
                        
            for adj in adjacent_lines:
                current_sensor = f"line_{adj}_i"
                current_val = sensors.get(current_sensor, 0.0)
                if current_val > 0.95:
                    alert_msg = f"CASCADING_TRIP_RISK: Opening {target} blocked. Adjacent line {adj} is near thermal capacity limit: {current_val:.3f} pu (>0.95 pu)."
                    self.alerts.append(alert_msg)
                    logger.warning(alert_msg)
                    return False, alert_msg

        return True, "Safety check passed."

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current safety guard state.
        """
        # Keep alerts list length capped (max 50)
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
            
        return {
            "timestamp": int(time.time() * 1000),
            "emergency_stop_active": self.emergency_stop_active,
            "alerts": self.alerts,
            "status": "EMERGENCY_STOP" if self.emergency_stop_active else ("WARNING" if self.alerts else "NOMINAL")
        }
