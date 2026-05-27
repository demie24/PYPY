import time
import random
import logging
from typing import Dict, Any, List, Optional
from hardware_state_manager import HardwareStateManager
from relay_controller import RelayController

logger = logging.getLogger("hardware.plc_interface")

class PLCInterface:
    def __init__(self, state_manager: HardwareStateManager, relay_controller: RelayController):
        self.state_manager = state_manager
        self.relay_controller = relay_controller
        self.device_id = "plc"
        self.comms_failure = False
        self.latency_spike = False
        
        # Mappings: breaker indices to breaker line IDs
        self.breakers_list = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        
    def set_comms_failure(self, state: bool):
        self.comms_failure = state
        logger.info(f"PLC comms failure injected state: {state}")
        
    def set_latency_spike(self, state: bool):
        self.latency_spike = state
        logger.info(f"PLC latency spike injected state: {state}")
        
    def _simulate_delay(self):
        if self.latency_spike:
            time.sleep(random.uniform(0.20, 0.40))
        else:
            time.sleep(random.uniform(0.02, 0.05))
            
    def read_coils(self, address: int, count: int) -> Optional[List[int]]:
        """
        Function Code 0x01: Read Coils (mapped to relay target status).
        Breakers coils start at address 0x0001 (1-indexed Modbus).
        """
        if self.comms_failure:
            self.state_manager.decay_trust(self.device_id, 0.1)
            return None
            
        self._simulate_delay()
        
        results = []
        for addr in range(address, address + count):
            idx = addr - 1 # Translate to 0-indexed list
            if 0 <= idx < len(self.breakers_list):
                rid = self.breakers_list[idx]
                state = self.state_manager.relays[rid]["coil"]
                results.append(1 if state == "CLOSED" else 0)
            else:
                results.append(0)
        return results
        
    def read_discrete_inputs(self, address: int, count: int) -> Optional[List[int]]:
        """
        Function Code 0x02: Read Discrete Inputs (mapped to relay auxiliary feedback contacts).
        Aux feedback contacts start at address 0x1001.
        """
        if self.comms_failure:
            self.state_manager.decay_trust(self.device_id, 0.1)
            return None
            
        self._simulate_delay()
        
        results = []
        for addr in range(address, address + count):
            idx = addr - 0x1001
            if 0 <= idx < len(self.breakers_list):
                rid = self.breakers_list[idx]
                state = self.state_manager.relays[rid]["feedback"]
                results.append(1 if state == "CLOSED" else 0)
            else:
                results.append(0)
        return results
        
    def read_input_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        Function Code 0x04: Read Input Registers (mapped to bus voltage sensors).
        Registers start at address 0x3001. Scaled x1000.
        """
        if self.comms_failure:
            self.state_manager.decay_trust(self.device_id, 0.1)
            return None
            
        self._simulate_delay()
        
        results = []
        for addr in range(address, address + count):
            bus_idx = addr - 0x3001 + 1 # Bus 1 to 9
            sensor_id = f"bus_{bus_idx}_v"
            if sensor_id in self.state_manager.sensors:
                val = self.state_manager.sensors[sensor_id]
                results.append(int(val * 1000))
            else:
                results.append(0)
        return results
        
    def write_single_coil(self, address: int, value: int) -> bool:
        """
        Function Code 0x05: Write Single Coil (mapped to breaker control).
        Coils start at address 0x0001. Value: 1 (CLOSED/CLOSE), 0 (OPEN).
        """
        if self.comms_failure:
            self.state_manager.decay_trust(self.device_id, 0.1)
            return False
            
        self._simulate_delay()
        
        idx = address - 1
        if 0 <= idx < len(self.breakers_list):
            rid = self.breakers_list[idx]
            target_state = "CLOSED" if value == 1 else "OPEN"
            success, msg = self.relay_controller.trigger_switching(rid, target_state)
            
            if success:
                logger.info(f"PLC write single coil success on coil {address} (Relay {rid}) -> {target_state}")
                # Synchronize output GPIO pin on state manager (ESP32 side)
                pin = f"pin_{idx + 4 if idx < 3 else (idx + 9 if idx < 7 else idx + 10)}" # Pin maps
                # Wait, we can just look up the pin mapping in a simpler way if needed,
                # but since state manager handles update_relay_state, that's already doing it!
                return True
            else:
                logger.warning(f"PLC write single coil failed on coil {address}: {msg}")
                return False
                
        return False
        
    def read_heartbeat_latency(self) -> float:
        if self.comms_failure:
            return -1.0
        if self.latency_spike:
            return random.uniform(300.0, 600.0)
        return random.uniform(20.0, 45.0)
        
    def run_heartbeat_cycle(self) -> Dict[str, Any]:
        latency = self.read_heartbeat_latency()
        if latency >= 0:
            self.state_manager.update_device_heartbeat(self.device_id, latency)
            dev_status = self.state_manager.devices[self.device_id]
            return {
                "timestamp": int(time.time() * 1000),
                "device_id": self.device_id,
                "status": "ONLINE",
                "latency_ms": round(latency, 2),
                "trust": dev_status["trust"]
            }
        else:
            self.state_manager.check_timeouts()
            dev_status = self.state_manager.devices[self.device_id]
            return {
                "timestamp": int(time.time() * 1000),
                "device_id": self.device_id,
                "status": "OFFLINE",
                "latency_ms": -1.0,
                "trust": dev_status["trust"]
            }
            
    def get_telemetry_payload(self) -> Dict[str, Any]:
        return {
            "timestamp": int(time.time() * 1000),
            "device_id": self.device_id,
            "breakers_list": self.breakers_list,
            "comms_failure": self.comms_failure,
            "latency_spike": self.latency_spike
        }
