import time
import random
import logging
import math
from typing import Dict, Any, Optional
from sensor_interface import SensorInterface
from hardware_state_manager import HardwareStateManager

logger = logging.getLogger("hardware.virtual_sensor_faults")

class VirtualSensorFaults(SensorInterface):
    def __init__(self, state_manager: HardwareStateManager):
        super().__init__(state_manager)
        
        # Sensor Fault Registries
        # Mappings of sensor_id (e.g. "bus_1_v", "line_L1_4_i") to configurations
        self.spoofing_biases: Dict[str, float] = {}
        
        # Mappings of sensor_id to corruption string: "NaN", "OOB", "STUCK"
        self.corruption_types: Dict[str, str] = {}
        self.stuck_values: Dict[str, float] = {}
        
        # Mappings of breaker_id (e.g. "L4_5") to fake feedback state ("OPEN", "CLOSED")
        self.fake_breaker_feedback: Dict[str, str] = {}

    def set_spoofing_bias(self, sensor_id: str, bias: float):
        self.spoofing_biases[sensor_id] = bias
        logger.info(f"Sensor spoofing bias set for {sensor_id}: {bias}")

    def remove_spoofing_bias(self, sensor_id: str):
        if sensor_id in self.spoofing_biases:
            del self.spoofing_biases[sensor_id]
            logger.info(f"Sensor spoofing bias removed for {sensor_id}")

    def set_corruption(self, sensor_id: str, corr_type: str, stuck_val: float = 1.0):
        """
        Configure telemetry corruption: "NaN", "OOB" (Out-of-bounds), "STUCK"
        """
        if corr_type in ["NaN", "OOB", "STUCK", "NONE"]:
            if corr_type == "NONE":
                self.remove_corruption(sensor_id)
            else:
                self.corruption_types[sensor_id] = corr_type
                if corr_type == "STUCK":
                    self.stuck_values[sensor_id] = stuck_val
                logger.info(f"Sensor corruption set for {sensor_id}: type={corr_type}")

    def remove_corruption(self, sensor_id: str):
        if sensor_id in self.corruption_types:
            del self.corruption_types[sensor_id]
        if sensor_id in self.stuck_values:
            del self.stuck_values[sensor_id]
        logger.info(f"Sensor corruption removed for {sensor_id}")

    def set_fake_breaker_feedback(self, breaker_id: str, feedback: Optional[str]):
        if feedback in ["OPEN", "CLOSED", "MISMAPPED"]:
            self.fake_breaker_feedback[breaker_id] = feedback
            logger.info(f"Fake breaker feedback set for {breaker_id}: {feedback}")
        else:
            if breaker_id in self.fake_breaker_feedback:
                del self.fake_breaker_feedback[breaker_id]
                logger.info(f"Fake breaker feedback removed for {breaker_id}")

    def clear_sensor_faults(self):
        self.spoofing_biases.clear()
        self.corruption_types.clear()
        self.stuck_values.clear()
        self.fake_breaker_feedback.clear()
        logger.info("All virtual sensor faults cleared.")

    def _apply_faults(self, sensor_id: str, base_val: float) -> float:
        """
        Applies configured bias or corruption to a sensor value.
        """
        # 1. Check corruption
        corr = self.corruption_types.get(sensor_id)
        if corr:
            if corr == "NaN":
                return float('nan')
            elif corr == "OOB":
                # Returns high out-of-bounds values (e.g. 1.80 p.u. or 999.0 deg)
                return 1.85 if "_v" in sensor_id else 5.0
            elif corr == "STUCK":
                return self.stuck_values.get(sensor_id, base_val)
                
        # 2. Check spoofing bias
        bias = self.spoofing_biases.get(sensor_id, 0.0)
        return max(0.0, base_val + bias)

    def simulate_sensor_sweep(self, twin_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wraps simulator sweep with sensor faults.
        """
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
        
        # 1. Voltages (PTs)
        for bid, bus in twin_buses.items():
            voltage = bus.get("voltage_pu", 1.0)
            noise = random.normalvariate(0, 0.003) if self.noise_enabled else 0.0
            drift = self.drifts.get(bid.lower() + "_v", 0.0) if self.drift_enabled else 0.0
            
            measured_v = max(0.0, round(voltage + noise + drift, 4))
            sensor_id = f"{bid.lower()}_v"
            
            # Apply Fault models
            final_v = self._apply_faults(sensor_id, measured_v)
            self.state_manager.update_sensor_value(sensor_id, final_v)
            
            sensor_data["buses"][bid] = {
                "voltage_pu": final_v,
                "angle_rad": bus.get("angle_rad", 0.0),
                "P_mw": bus.get("P_mw", 0.0),
                "Q_mvar": bus.get("Q_mvar", 0.0)
            }
            
        # 2. Line Currents (CTs) & Temps
        for lid, line in twin_lines.items():
            current = line.get("current_pu", 0.0)
            noise = random.normalvariate(0, 0.005) if self.noise_enabled else 0.0
            measured_i = max(0.0, round(current + noise, 4))
            
            sensor_id_i = f"line_{lid}_i"
            final_i = self._apply_faults(sensor_id_i, measured_i)
            self.state_manager.update_sensor_value(sensor_id_i, final_i)
            
            # Temps
            ambient_temp = 25.0
            temp_increase = 30.0 * (final_i ** 2) if not math.isnan(final_i) else 0.0
            measured_temp = round(ambient_temp + temp_increase + random.uniform(-0.5, 0.5), 1)
            
            sensor_id_t = f"line_{lid}_temp"
            final_t = self._apply_faults(sensor_id_t, measured_temp)
            self.state_manager.update_sensor_value(sensor_id_t, final_t)
            
            sensor_data["lines"][lid] = {
                "current_pu": final_i,
                "current_amp": round(final_i * 500, 2) if not math.isnan(final_i) else float('nan'),
                "temperature_c": final_t,
                "capacity_pct": line.get("capacity_pct", 0.0)
            }
            
        # 3. Breaker feedbacks
        for bid, state in twin_breakers.items():
            fake_state = self.fake_breaker_feedback.get(bid)
            if fake_state:
                # Override contact feedback
                if fake_state == "MISMAPPED":
                    # Invert state to simulate mismapped feedback wires
                    aux_feedback = "OPEN" if state == "CLOSED" else "CLOSED"
                else:
                    aux_feedback = fake_state
                    
                # Proactively update state manager to trigger health/trust degradation
                # We update the state manager relay's feedback directly so that the next
                # loop checks mismatch and decays trust statefully
                coil_state = self.state_manager.relays[bid]["coil"]
                self.state_manager.update_relay_state(bid, coil_state, aux_feedback)
            else:
                relay_data = self.state_manager.relays.get(bid)
                aux_feedback = relay_data["feedback"] if relay_data else state
                
            sensor_data["breakers"][bid] = aux_feedback
            
        return sensor_data
