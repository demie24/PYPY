import time
import random
import json
import logging
from typing import Dict, Any
from hardware_state_manager import HardwareStateManager

logger = logging.getLogger("hardware.esp32_bridge")

class ESP32Bridge:
    def __init__(self, state_manager: HardwareStateManager, relay_controller=None):
        self.state_manager = state_manager
        self.relay_controller = relay_controller
        self.device_id = "esp32"
        self.comms_failure = False
        self.latency_spike = False
        
        # Mappings of output pins to breaker control targets
        self.pin_to_relay = {
            "pin_4": "L1_4",
            "pin_5": "L2_7",
            "pin_6": "L3_9",
            "pin_12": "L4_5",
            "pin_13": "L4_9",
            "pin_14": "L5_6",
            "pin_15": "L6_7",
            "pin_16": "L7_8",
            "pin_17": "L8_9"
        }
        
        self.output_to_feedback = {
            "pin_4": "pin_21",
            "pin_5": "pin_22",
            "pin_6": "pin_23",
            "pin_12": "pin_25",
            "pin_13": "pin_26",
            "pin_14": "pin_27",
            "pin_15": "pin_32",
            "pin_16": "pin_33",
            "pin_17": "pin_34"
        }
        
    def set_comms_failure(self, state: bool):
        self.comms_failure = state
        logger.info(f"ESP32 comms failure injected state: {state}")
        
    def set_latency_spike(self, state: bool):
        self.latency_spike = state
        logger.info(f"ESP32 latency spike injected state: {state}")
        
    def execute_gpio_write(self, pin: str, val: int) -> bool:
        """
        Simulates writing a value to an ESP32 GPIO pin.
        Returns True if successful, False if communication failure.
        """
        if self.comms_failure:
            logger.warning(f"ESP32 Write failed on {pin}: Communication offline.")
            self.state_manager.decay_trust(self.device_id, 0.1)
            return False
            
        # Simulate physical write delay
        delay = random.uniform(0.1, 0.3) if self.latency_spike else random.uniform(0.01, 0.03)
        time.sleep(delay)
        
        if pin in self.state_manager.gpio:
            self.state_manager.update_gpio_state(pin, val)
            logger.info(f"ESP32 pin {pin} written successfully to {val}")
            
            # If this output pin controls a relay coil, propagate it to state manager
            relay_id = self.pin_to_relay.get(pin)
            if relay_id:
                coil_val = "CLOSED" if val == 1 else "OPEN"
                feedback_pin = self.output_to_feedback.get(pin)
                feedback_val = coil_val
                
                if self.relay_controller:
                    self.relay_controller.trigger_switching(relay_id, coil_val)
                else:
                    self.state_manager.update_relay_state(relay_id, coil_val, feedback_val)
                    
                if feedback_pin in self.state_manager.gpio:
                    self.state_manager.update_gpio_state(feedback_pin, val)
                    
            return True
        return False
        
    def read_heartbeat_latency(self) -> float:
        """
        Simulates round-trip ping time in milliseconds.
        """
        if self.comms_failure:
            return -1.0
        if self.latency_spike:
            return random.uniform(250.0, 500.0)
        return random.uniform(10.0, 35.0)
        
    def run_heartbeat_cycle(self) -> Dict[str, Any]:
        """
        Generates and logs a heartbeat frame.
        """
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
        """
        Compiles the ESP32 specific telemetry packet.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "device_id": self.device_id,
            "gpio_pins": {pin: val for pin, val in self.state_manager.gpio.items() if pin in self.pin_to_relay or f"pin_{int(pin.split('_')[1]) - 17}" in self.pin_to_relay},
            "comms_failure": self.comms_failure,
            "latency_spike": self.latency_spike
        }
