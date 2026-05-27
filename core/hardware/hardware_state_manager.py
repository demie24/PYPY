import time
import logging
from typing import Dict, Any

logger = logging.getLogger("hardware.state_manager")

class HardwareStateManager:
    def __init__(self):
        # Device Registry
        self.devices = {
            "esp32": {
                "name": "ESP32 Controller",
                "status": "ONLINE",
                "latency_ms": 20.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "microcontroller"
            },
            "plc": {
                "name": "Industrial Modbus PLC",
                "status": "ONLINE",
                "latency_ms": 30.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "plc"
            }
        }
        
        # Relay States (OPEN/CLOSED) and auxiliary contact feedback (OPEN/CLOSED)
        # Mapping standard transmission line IDs
        self.relays = {
            "L1_4": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L2_7": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L3_9": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L4_5": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L4_9": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L5_6": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L6_7": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()},
            "L7_8": {"coil": "OPEN", "feedback": "OPEN", "last_changed": time.time()},
            "L8_9": {"coil": "CLOSED", "feedback": "CLOSED", "last_changed": time.time()}
        }
        
        # GPIO Pins mapping (ESP32)
        # Let's map virtual pins to relay coils (output pins) and auxiliary feedback (input pins)
        self.gpio = {
            "pin_4": 1,   # Relay L1_4 coil output
            "pin_5": 1,   # Relay L2_7 coil output
            "pin_6": 1,   # Relay L3_9 coil output
            "pin_12": 1,  # Relay L4_5 coil output
            "pin_13": 1,  # Relay L4_9 coil output
            "pin_14": 1,  # Relay L5_6 coil output
            "pin_15": 1,  # Relay L6_7 coil output
            "pin_16": 0,  # Relay L7_8 coil output
            "pin_17": 1,  # Relay L8_9 coil output
            
            "pin_21": 1,  # Relay L1_4 feedback input
            "pin_22": 1,  # Relay L2_7 feedback input
            "pin_23": 1,  # Relay L3_9 feedback input
            "pin_25": 1,  # Relay L4_5 feedback input
            "pin_26": 1,  # Relay L4_9 feedback input
            "pin_27": 1,  # Relay L5_6 feedback input
            "pin_32": 1,  # Relay L6_7 feedback input
            "pin_33": 0,  # Relay L7_8 feedback input
            "pin_34": 1   # Relay L8_9 feedback input
        }
        
        # Sensor values (voltage_pu, current_pu, temperature_c)
        self.sensors = {
            "bus_1_v": 1.04,
            "bus_2_v": 1.025,
            "bus_3_v": 1.025,
            "bus_4_v": 1.0,
            "bus_5_v": 1.0,
            "bus_6_v": 1.0,
            "bus_7_v": 1.0,
            "bus_8_v": 1.0,
            "bus_9_v": 1.0,
            
            "line_L1_4_i": 0.5,
            "line_L2_7_i": 0.5,
            "line_L3_9_i": 0.5,
            "line_L4_5_i": 0.5,
            "line_L4_9_i": 0.5,
            "line_L5_6_i": 0.5,
            "line_L6_7_i": 0.5,
            "line_L7_8_i": 0.0,
            "line_L8_9_i": 0.5,
            
            "line_L1_4_temp": 45.2,
            "line_L2_7_temp": 43.1,
            "line_L3_9_temp": 41.8,
            "line_L4_5_temp": 48.9,
            "line_L4_9_temp": 49.5,
            "line_L5_6_temp": 52.3,
            "line_L6_7_temp": 46.7,
            "line_L7_8_temp": 25.0,
            "line_L8_9_temp": 47.1
        }
        
        self.relay_to_pins = {
            "L1_4": {"coil": "pin_4", "feedback": "pin_21"},
            "L2_7": {"coil": "pin_5", "feedback": "pin_22"},
            "L3_9": {"coil": "pin_6", "feedback": "pin_23"},
            "L4_5": {"coil": "pin_12", "feedback": "pin_25"},
            "L4_9": {"coil": "pin_13", "feedback": "pin_26"},
            "L5_6": {"coil": "pin_14", "feedback": "pin_27"},
            "L6_7": {"coil": "pin_15", "feedback": "pin_32"},
            "L7_8": {"coil": "pin_16", "feedback": "pin_33"},
            "L8_9": {"coil": "pin_17", "feedback": "pin_34"}
        }
        
        self.last_update = time.time()
        
    def update_device_heartbeat(self, device_id: str, latency_ms: float):
        if device_id in self.devices:
            dev = self.devices[device_id]
            dev["status"] = "ONLINE"
            dev["latency_ms"] = latency_ms
            dev["last_seen"] = time.time()
            
            # Decay trust if latency is excessive (> 200ms)
            if latency_ms > 200.0:
                self.decay_trust(device_id, 0.05)
            else:
                self.recover_trust(device_id, 0.01)
                
    def decay_trust(self, device_id: str, penalty: float):
        if device_id in self.devices:
            dev = self.devices[device_id]
            dev["trust"] = max(0.1, round(dev["trust"] - penalty, 3))
            
    def recover_trust(self, device_id: str, recovery: float):
        if device_id in self.devices:
            dev = self.devices[device_id]
            dev["trust"] = min(1.0, round(dev["trust"] + recovery, 3))
            
    def update_relay_state(self, relay_id: str, coil: str, feedback: str):
        if relay_id in self.relays:
            self.relays[relay_id]["coil"] = coil
            self.relays[relay_id]["feedback"] = feedback
            self.relays[relay_id]["last_changed"] = time.time()
            
            # Sync GPIO pins
            pins = self.relay_to_pins.get(relay_id)
            if pins:
                coil_pin = pins["coil"]
                feed_pin = pins["feedback"]
                if coil_pin in self.gpio:
                    self.gpio[coil_pin] = 1 if coil == "CLOSED" else 0
                if feed_pin in self.gpio:
                    self.gpio[feed_pin] = 1 if feedback == "CLOSED" else 0
            
            # Check for relay command-feedback discrepancies
            # (e.g. coil is CLOSED but auxiliary feedback contact says OPEN)
            if coil != feedback:
                logger.warning(f"Relay alignment mismatch on {relay_id}: coil={coil}, feedback={feedback}")
                # Degrade trust on whichever device is controlling that relay
                if relay_id in ["L7_8", "L8_9", "L6_7"]:
                    self.decay_trust("plc", 0.1)
                else:
                    self.decay_trust("esp32", 0.1)
            
    def update_gpio_state(self, pin: str, value: int):
        if pin in self.gpio:
            self.gpio[pin] = value
            
    def update_sensor_value(self, sensor_id: str, value: float):
        if sensor_id in self.sensors:
            self.sensors[sensor_id] = value
            
    def check_timeouts(self):
        """
        Flags devices offline if their heartbeat is missing for > 5.0 seconds.
        """
        now = time.time()
        for dev_id, dev in self.devices.items():
            if now - dev["last_seen"] > 5.0:
                if dev["status"] != "OFFLINE":
                    dev["status"] = "OFFLINE"
                    logger.error(f"Device offline timeout: {dev_id}")
                self.decay_trust(dev_id, 0.2)
                dev["latency_ms"] = -1.0
                
    def get_device_health(self) -> Dict[str, Any]:
        self.check_timeouts()
        return {
            "timestamp": int(time.time() * 1000),
            "devices": self.devices
        }
        
    def get_all_states(self) -> Dict[str, Any]:
        self.check_timeouts()
        return {
            "timestamp": int(time.time() * 1000),
            "devices": self.devices,
            "relays": self.relays,
            "gpio": self.gpio,
            "sensors": self.sensors
        }
