import time
import random
import logging
from typing import Dict, Any, List, Optional
from plc_interface import PLCInterface
from hardware_state_manager import HardwareStateManager
from relay_controller import RelayController

logger = logging.getLogger("hardware.virtual_plc")

class VirtualPLC(PLCInterface):
    def __init__(self, state_manager: HardwareStateManager, relay_controller: RelayController):
        super().__init__(state_manager, relay_controller)
        self.write_delay_duration = 0.0  # seconds delay for writing coils
        self.modbus_exception_rate = 0.0  # rate of simulated Modbus exceptions (returns None/Error)
        self.is_connected = True
        self.reconnect_time = 0.0
        self.reconnect_duration = 3.0  # seconds to reconnect after comms restored
        
        # Delayed Command queue
        # List of dicts: {"execute_time": float, "address": int, "value": int}
        self.write_queue: List[Dict[str, Any]] = []

    def set_write_delay(self, duration: float):
        self.write_delay_duration = max(0.0, duration)
        logger.info(f"PLC Modbus write delay set to: {self.write_delay_duration}s")
        
    def set_modbus_exception_rate(self, rate: float):
        self.modbus_exception_rate = max(0.0, min(1.0, rate))
        logger.info(f"PLC Modbus exception rate set to: {self.modbus_exception_rate}")

    def set_comms_failure(self, state: bool):
        super().set_comms_failure(state)
        if state:
            self.is_connected = False
            self.reconnect_time = 0.0
            logger.warning("PLC Modbus server offline (DoS injected).")
        else:
            if not self.is_connected:
                self.reconnect_time = time.time() + self.reconnect_duration
                logger.info(f"PLC comms fault cleared. Reconnection scheduled in {self.reconnect_duration}s.")

    def _should_raise_exception(self) -> bool:
        if random.random() < self.modbus_exception_rate:
            logger.warning("Simulated Modbus exception raised.")
            self.state_manager.decay_trust(self.device_id, 0.05)
            return True
        return False

    def read_coils(self, address: int, count: int) -> Optional[List[int]]:
        if not self.is_connected or self._should_raise_exception():
            return None
        return super().read_coils(address, count)
        
    def read_discrete_inputs(self, address: int, count: int) -> Optional[List[int]]:
        if not self.is_connected or self._should_raise_exception():
            return None
        return super().read_discrete_inputs(address, count)
        
    def read_input_registers(self, address: int, count: int) -> Optional[List[int]]:
        if not self.is_connected or self._should_raise_exception():
            return None
        return super().read_input_registers(address, count)

    def write_single_coil(self, address: int, value: int) -> bool:
        if not self.is_connected or self._should_raise_exception():
            return False
            
        if self.write_delay_duration > 0.0:
            exec_time = time.time() + self.write_delay_duration
            self.write_queue.append({
                "execute_time": exec_time,
                "address": address,
                "value": value
            })
            logger.info(f"PLC Modbus command queued for address {address} (Value: {value}). Executing in {self.write_delay_duration}s.")
            return True
        else:
            return super().write_single_coil(address, value)

    def process_write_queue(self):
        """
        Processes and triggers queued coil writes when their delay timer expires.
        Must be called in the execution loop.
        """
        now = time.time()
        expired = []
        
        for cmd in self.write_queue:
            if now >= cmd["execute_time"]:
                expired.append(cmd)
                
        for cmd in expired:
            self.write_queue.remove(cmd)
            # Directly call super to bypass delay queue checking
            logger.info(f"Executing deferred PLC write on coil address {cmd['address']} -> {cmd['value']}")
            super().write_single_coil(cmd["address"], cmd["value"])

    def run_heartbeat_cycle(self) -> Dict[str, Any]:
        now = time.time()
        
        # Handle reconnection
        if not self.is_connected and self.reconnect_time > 0.0 and now >= self.reconnect_time:
            self.is_connected = True
            self.reconnect_time = 0.0
            self.comms_failure = False
            logger.info("PLC Modbus connection re-established statefully.")
            
        if not self.is_connected:
            self.state_manager.check_timeouts()
            self.state_manager.decay_trust(self.device_id, 0.1)
            dev_status = self.state_manager.devices[self.device_id]
            return {
                "timestamp": int(now * 1000),
                "device_id": self.device_id,
                "status": "OFFLINE",
                "latency_ms": -1.0,
                "trust": dev_status["trust"]
            }
            
        # Nominal heartbeat
        latency = self.read_heartbeat_latency()
        self.state_manager.update_device_heartbeat(self.device_id, latency)
        dev_status = self.state_manager.devices[self.device_id]
        return {
            "timestamp": int(now * 1000),
            "device_id": self.device_id,
            "status": "ONLINE",
            "latency_ms": round(latency, 2),
            "trust": dev_status["trust"]
        }

    def get_telemetry_payload(self) -> Dict[str, Any]:
        payload = super().get_telemetry_payload()
        payload.update({
            "is_connected": self.is_connected,
            "write_delay": self.write_delay_duration,
            "modbus_exception_rate": self.modbus_exception_rate,
            "reconnect_time_left": max(0.0, round(self.reconnect_time - time.time(), 2)) if self.reconnect_time > 0.0 else 0.0,
            "queued_commands_count": len(self.write_queue)
        })
        return payload
