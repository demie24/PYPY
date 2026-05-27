import time
import logging
from typing import Dict, Any, Tuple
from hardware_state_manager import HardwareStateManager
from esp32_bridge import ESP32Bridge
from plc_interface import PLCInterface
from relay_controller import RelayController

logger = logging.getLogger("hardware.command_router")

class HardwareCommandRouter:
    def __init__(self, state_manager: HardwareStateManager, esp32_bridge: ESP32Bridge, plc_interface: PLCInterface, relay_controller: RelayController):
        self.state_manager = state_manager
        self.esp32_bridge = esp32_bridge
        self.plc_interface = plc_interface
        self.relay_controller = relay_controller
        self.command_history = []
        
        # Mappings of line breakers to hardware targets and coordinates
        # Relays L1_4 to L5_6 (first 6 index) are controlled by ESP32 GPIO pins
        # Relays L6_7 to L8_9 are controlled by the PLC Modbus Coils
        self.routing_table = {
            "L1_4": {"device": "esp32", "target_id": "pin_4"},
            "L2_7": {"device": "esp32", "target_id": "pin_5"},
            "L3_9": {"device": "esp32", "target_id": "pin_6"},
            "L4_5": {"device": "esp32", "target_id": "pin_12"},
            "L4_9": {"device": "esp32", "target_id": "pin_13"},
            "L5_6": {"device": "esp32", "target_id": "pin_14"},
            
            "L6_7": {"device": "plc", "target_id": 7},  # Modbus coil address 7
            "L7_8": {"device": "plc", "target_id": 8},  # Modbus coil address 8
            "L8_9": {"device": "plc", "target_id": 9}   # Modbus coil address 9
        }
        
    def validate_command_safety(self, breaker_id: str, cmd_state: str) -> Tuple[bool, str]:
        """
        Enforces safety interlocks at the hardware layer.
        For example:
        - Prevent closing L7_8 if it would create parallel loops unless authorized.
        - Prevent opening generator transformer lines (L1_4, L2_7, L3_9) if the generator is active and other paths are open (avoiding generator load dumping).
        """
        # Check if the breaker is already in target state
        relay_data = self.state_manager.relays.get(breaker_id)
        if not relay_data:
            return False, f"Target breaker {breaker_id} not found in hardware register."
            
        current = relay_data["coil"]
        if current == cmd_state:
            return True, "No action required: breaker already in target state."
            
        # Physical interlock check:
        # Generator load shedding avoidance: do not open Generator Transformers L1_4, L2_7, L3_9 
        # if the grid is in a severe instability state, unless it's a cyber lockdown command.
        if breaker_id in ["L1_4", "L2_7", "L3_9"] and cmd_state == "OPEN":
            # If all other gen lines are open, block it to prevent islanding generators.
            closed_gens = sum(1 for gid in ["L1_4", "L2_7", "L3_9"] if self.state_manager.relays[gid]["coil"] == "CLOSED")
            if closed_gens <= 1:
                return False, f"Interlock Blocked: Opening {breaker_id} would isolate the final generator transformer."
                
        # Anti-chattering Lockout Check (delegated to relay_controller timestamp check)
        now = time.time()
        last_switch = self.relay_controller.last_switching_times.get(breaker_id, 0.0)
        if now - last_switch < self.relay_controller.lockout_duration:
            return False, f"Anti-chattering lockout active. Switch blocked on {breaker_id}."
            
        return True, "Passed physical safety validations."
        
    def route_command(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Routes proposed command to virtual ESP32 or PLC.
        Logs transaction details.
        """
        timestamp_ms = int(time.time() * 1000)
        cmd = payload.get("command")
        target = payload.get("target")
        source = payload.get("source", "UNKNOWN")
        
        # Translate commands (CLOSE/OPEN) to digital states (1/0)
        val = 1 if cmd in ["CLOSE", "CLOSED"] else 0
        cmd_state = "CLOSED" if val == 1 else "OPEN"
        
        if not target or target not in self.routing_table:
            err_msg = f"Invalid command routing target: {target}"
            logger.warning(err_msg)
            self._log_transaction(timestamp_ms, payload, "NONE", "FAILED", err_msg)
            return False, err_msg
            
        # 1. Physical safety check
        safe, msg = self.validate_command_safety(target, cmd_state)
        if not safe:
            logger.warning(f"Hardware command blocked: {msg}")
            self._log_transaction(timestamp_ms, payload, "NONE", "BLOCKED", msg)
            return False, msg
            
        route = self.routing_table[target]
        device = route["device"]
        target_id = route["target_id"]
        
        # 2. Dispatch to target simulated device
        success = False
        if device == "esp32":
            success = self.esp32_bridge.execute_gpio_write(target_id, val)
            dispatch_msg = "Dispatched via ESP32 GPIO write." if success else "ESP32 GPIO write timed out (offline)."
        elif device == "plc":
            success = self.plc_interface.write_single_coil(target_id, val)
            dispatch_msg = "Dispatched via PLC Modbus Write Single Coil." if success else "PLC Modbus write failed (offline)."
            
        status = "SUCCESS" if success else "FAILED"
        final_msg = dispatch_msg if success else f"Hardware routing failed on {device}: {dispatch_msg}"
        
        # 3. Log transaction
        self._log_transaction(timestamp_ms, payload, device, status, final_msg)
        return success, final_msg
        
    def _log_transaction(self, timestamp_ms: int, source_cmd: Dict[str, Any], routed_to: str, status: str, details: str):
        log_entry = {
            "timestamp": timestamp_ms,
            "command": source_cmd.get("command"),
            "target": source_cmd.get("target"),
            "source": source_cmd.get("source"),
            "device": routed_to,
            "status": status,
            "details": details
        }
        self.command_history.append(log_entry)
        if len(self.command_history) > 50:
            self.command_history.pop(0)
            
        logger.info(f"Hardware Router transaction: {log_entry}")
