import unittest
import sys
import os
import math

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from virtual_sensor_faults import VirtualSensorFaults

class TestVirtualSensorFaults(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.sensor = VirtualSensorFaults(self.mgr)
        
        # Base twin telemetry payload for sweep
        self.twin_payload = {
            "timestamp": 1000,
            "buses": {
                "Bus_5": {"voltage_pu": 0.99, "angle_rad": 0.05, "P_mw": 50, "Q_mvar": 10}
            },
            "lines": {
                "L1_4": {"current_pu": 0.45, "capacity_pct": 45.0}
            },
            "breakers": {
                "L4_5": "CLOSED"
            }
        }
        
    def test_nominal_sweep(self):
        self.sensor.noise_enabled = False
        self.sensor.drift_enabled = False
        sweep = self.sensor.simulate_sensor_sweep(self.twin_payload)
        
        # Verify basic mappings
        self.assertEqual(sweep["buses"]["Bus_5"]["voltage_pu"], 0.99)
        self.assertEqual(sweep["lines"]["L1_4"]["current_pu"], 0.45)
        self.assertEqual(sweep["breakers"]["L4_5"], "CLOSED")
        
    def test_voltage_spoofing_bias(self):
        self.sensor.noise_enabled = False
        self.sensor.set_spoofing_bias("bus_5_v", -0.15)
        
        sweep = self.sensor.simulate_sensor_sweep(self.twin_payload)
        # Expected voltage: 0.99 - 0.15 = 0.84 pu
        self.assertAlmostEqual(sweep["buses"]["Bus_5"]["voltage_pu"], 0.84)
        self.assertAlmostEqual(self.mgr.sensors["bus_5_v"], 0.84)
        
    def test_nan_telemetry_corruption(self):
        self.sensor.set_corruption("bus_5_v", "NaN")
        sweep = self.sensor.simulate_sensor_sweep(self.twin_payload)
        
        self.assertTrue(math.isnan(sweep["buses"]["Bus_5"]["voltage_pu"]))
        self.assertTrue(math.isnan(self.mgr.sensors["bus_5_v"]))
        
    def test_out_of_bounds_telemetry_corruption(self):
        self.sensor.set_corruption("bus_5_v", "OOB")
        sweep = self.sensor.simulate_sensor_sweep(self.twin_payload)
        
        self.assertEqual(sweep["buses"]["Bus_5"]["voltage_pu"], 1.85)
        self.assertEqual(self.mgr.sensors["bus_5_v"], 1.85)
        
    def test_stuck_telemetry_corruption(self):
        self.sensor.set_corruption("bus_5_v", "STUCK", 0.91)
        sweep = self.sensor.simulate_sensor_sweep(self.twin_payload)
        
        self.assertEqual(sweep["buses"]["Bus_5"]["voltage_pu"], 0.91)
        self.assertEqual(self.mgr.sensors["bus_5_v"], 0.91)
        
    def test_fake_breaker_feedback_mismatch(self):
        # Override contact feedback to MISMAPPED (should invert CLOSED to OPEN)
        self.sensor.set_fake_breaker_feedback("L4_5", "MISMAPPED")
        sweep = self.sensor.simulate_sensor_sweep(self.twin_payload)
        
        self.assertEqual(sweep["breakers"]["L4_5"], "OPEN")
        # Check alignment mismatch statefully registered in state manager
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "OPEN")

if __name__ == "__main__":
    unittest.main()
