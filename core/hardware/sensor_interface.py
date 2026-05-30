import time
import random
import logging
from typing import Dict, Any
from core.hardware.hardware_state_manager import HardwareStateManager

logger = logging.getLogger("hardware.sensor_interface")

class SensorInterface:
    def __init__(self, state_manager: HardwareStateManager):
        self.state_manager = state_manager
        self.noise_enabled = True
        self.drift_enabled = False
        self.packet_loss_rate = 0.0  # 0.0 to 1.0
        
        # Calibration drifts per sensor
        self.drifts = {
            "bus_1_v": 0.0, "bus_2_v": 0.0, "bus_3_v": 0.0,
            "bus_4_v": 0.0, "bus_5_v": 0.0, "bus_6_v": 0.0,
            "bus_7_v": 0.0, "bus_8_v": 0.0, "bus_9_v": 0.0
        }
        
    def set_calibration_drift(self, sensor_id: str, drift: float):
        if sensor_id in self.drifts:
            self.drifts[sensor_id] = drift
            logger.info(f"Calibration drift set for {sensor_id}: {drift}")
            
    def simulate_sensor_sweep(self, twin_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes grid simulator telemetry to produce virtual physical sensor readings.
        Adds noise, drift offsets, thermal loading math, and simulates packets drop.
        """
        # 1. Packet drop simulation
        if random.random() < self.packet_loss_rate:
            logger.warning("Simulated sensor sweep packet dropped (packet loss).")
            return {}
            
        timestamp_ms = int(time.time() * 1000)
        sensor_data = {
            "timestamp": timestamp_ms,
            "buses": {},
            "lines": {},
            "breakers": {}
        }
        
        twin_state = twin_telemetry.get("state") or twin_telemetry
        twin_buses = twin_state.get("buses") or {}
        twin_lines = twin_state.get("lines") or {}
        twin_breakers = twin_state.get("breakers") or {}
        
        # 2. Voltage Sensors (PTs)
        for bid, bus in twin_buses.items():
            voltage = bus.get("voltage_pu", 1.0)
            
            # Apply Gaussian noise
            noise = random.normalvariate(0, 0.003) if self.noise_enabled else 0.0
            # Apply Calibration drift
            drift = self.drifts.get(bid.lower() + "_v", 0.0) if self.drift_enabled else 0.0
            
            measured_v = max(0.0, round(voltage + noise + drift, 4))
            sensor_id = f"{bid.lower()}_v"
            self.state_manager.update_sensor_value(sensor_id, measured_v)
            
            sensor_data["buses"][bid] = {
                "voltage_pu": measured_v,
                "angle_rad": bus.get("angle_rad", 0.0),
                "P_mw": bus.get("P_mw", 0.0),
                "Q_mvar": bus.get("Q_mvar", 0.0)
            }
            
        # 3. Current (CTs) & Temperature Sensors
        for lid, line in twin_lines.items():
            current = line.get("current_pu", 0.0)
            
            # Apply current sensor noise
            noise = random.normalvariate(0, 0.005) if self.noise_enabled else 0.0
            measured_i = max(0.0, round(current + noise, 4))
            sensor_id = f"line_{lid}_i"
            self.state_manager.update_sensor_value(sensor_id, measured_i)
            
            # Simulated Thermal Convection Dynamics
            # Temperature = Ambient (25.0) + constant * current_pu^2
            ambient_temp = 25.0
            temp_increase = 30.0 * (measured_i ** 2)
            measured_temp = round(ambient_temp + temp_increase + random.uniform(-0.5, 0.5), 1)
            temp_sensor_id = f"line_{lid}_temp"
            self.state_manager.update_sensor_value(temp_sensor_id, measured_temp)
            
            sensor_data["lines"][lid] = {
                "current_pu": measured_i,
                "current_amp": round(measured_i * 500, 2),
                "temperature_c": measured_temp,
                "capacity_pct": line.get("capacity_pct", 0.0)
            }
            
        # 4. Breaker auxiliary feedback status
        for bid, state in twin_breakers.items():
            # If the relay is currently transitioning in the hardware state manager, 
            # auxiliary contact feedback might reflect contact bounces or mechanical delays.
            # Otherwise, auxiliary contact matches the twin breaker state.
            relay_data = self.state_manager.relays.get(bid)
            if relay_data:
                aux_feedback = relay_data["feedback"]
            else:
                aux_feedback = state
                
            sensor_data["breakers"][bid] = aux_feedback
            
        return sensor_data
