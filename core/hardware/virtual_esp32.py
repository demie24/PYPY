import time
import random
import logging
from typing import Dict, Any
from core.hardware.esp32_bridge import ESP32Bridge
from core.hardware.hardware_state_manager import HardwareStateManager

logger = logging.getLogger("hardware.virtual_esp32")

class VirtualESP32(ESP32Bridge):
    def __init__(self, state_manager: HardwareStateManager, relay_controller=None):
        super().__init__(state_manager, relay_controller)
        self.packet_drop_rate = 0.0
        self.heartbeat_failure = False
        self.is_connected = True
        self.reconnect_time = 0.0
        self.reconnect_duration = 3.0  # seconds to reconnect after fault cleared
        
        # Base latency details
        self.base_latency = 15.0  # ms
        self.jitter = 5.0  # ms
        
    def set_packet_drop_rate(self, rate: float):
        self.packet_drop_rate = max(0.0, min(1.0, rate))
        logger.info(f"ESP32 packet drop rate set to: {self.packet_drop_rate}")
        
    def set_heartbeat_failure(self, state: bool):
        self.heartbeat_failure = state
        logger.info(f"ESP32 heartbeat failure state: {state}")
        
    def set_comms_failure(self, state: bool):
        """
        Overrides set_comms_failure to support stateful reconnect behavior.
        """
        # Call base setting
        super().set_comms_failure(state)
        
        if state:
            self.is_connected = False
            self.reconnect_time = 0.0
            logger.warning("ESP32 disconnected state active (DoS injected).")
        else:
            if not self.is_connected:
                # Start reconnection window timer
                self.reconnect_time = time.time() + self.reconnect_duration
                logger.info(f"ESP32 fault cleared. Reconnection scheduled in {self.reconnect_duration}s.")

    def _get_dynamic_latency(self) -> float:
        """
        Calculates dynamic WiFi latency with random jitter and spikes.
        """
        if self.latency_spike:
            return random.uniform(250.0, 500.0)
        
        # Normal distribution centered around base_latency with jitter
        lat = random.normalvariate(self.base_latency, self.jitter)
        return max(5.0, lat)

    def execute_gpio_write(self, pin: str, val: int) -> bool:
        """
        Simulates writing to virtual GPIO, checking connection status and packet drop rates.
        """
        # 1. Connection check
        if not self.is_connected:
            logger.warning(f"ESP32 Write failed on {pin}: Device is offline.")
            self.state_manager.decay_trust(self.device_id, 0.08)
            return False
            
        # 2. Packet drop simulation
        if random.random() < self.packet_drop_rate:
            logger.warning(f"ESP32 Write failed on {pin}: Packet dropped (drop rate={self.packet_drop_rate}).")
            self.state_manager.decay_trust(self.device_id, 0.04)
            return False
            
        # 3. Simulate WiFi Latency
        latency = self._get_dynamic_latency()
        time.sleep(latency / 1000.0)
        
        # 4. Perform write
        if pin in self.state_manager.gpio:
            self.state_manager.update_gpio_state(pin, val)
            logger.info(f"ESP32 pin {pin} written successfully to {val} (latency={latency:.1f}ms)")
            
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

    def run_heartbeat_cycle(self) -> Dict[str, Any]:
        """
        Stateful heartbeat cycle supporting auto-reconnection and failure injections.
        """
        now = time.time()
        
        # Stateful reconnection transition
        if not self.is_connected and self.reconnect_time > 0.0 and now >= self.reconnect_time:
            self.is_connected = True
            self.reconnect_time = 0.0
            self.comms_failure = False
            logger.info("ESP32 stateful reconnection complete. Heartbeat restored.")
            
        # Compile status
        if self.heartbeat_failure or not self.is_connected:
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
        latency = self._get_dynamic_latency()
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
            "packet_drop_rate": self.packet_drop_rate,
            "heartbeat_failure": self.heartbeat_failure,
            "reconnect_time_left": max(0.0, round(self.reconnect_time - time.time(), 2)) if self.reconnect_time > 0.0 else 0.0
        })
        return payload
