import unittest
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.sensor_interface import SensorInterface

class TestSensorInterface(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.sensor = SensorInterface(self.mgr)
        
        # Mock Digital Twin Telemetry
        self.mock_telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.04, "angle_rad": 0.0, "P_mw": 0, "Q_mvar": 0},
                    "Bus_5": {"voltage_pu": 1.00, "angle_rad": -0.1, "P_mw": 125, "Q_mvar": 50}
                },
                "lines": {
                    "L1_4": {"current_pu": 0.6, "current_amp": 300, "P_mw": 60, "Q_mvar": 20, "capacity_pct": 20.0},
                    "L4_5": {"current_pu": 1.2, "current_amp": 600, "P_mw": 120, "Q_mvar": 40, "capacity_pct": 40.0}
                },
                "breakers": {
                    "L1_4": "CLOSED",
                    "L4_5": "CLOSED"
                }
            }
        }
        
    def test_sensor_sweep_nominal(self):
        sweep = self.sensor.simulate_sensor_sweep(self.mock_telemetry)
        
        # Verify buses telemetry mapped and noisy
        self.assertIn("Bus_1", sweep["buses"])
        self.assertIn("Bus_5", sweep["buses"])
        self.assertAlmostEqual(sweep["buses"]["Bus_1"]["voltage_pu"], 1.04, delta=0.02)
        
        # Verify lines current and temperatures mapped
        self.assertIn("L1_4", sweep["lines"])
        self.assertIn("L4_5", sweep["lines"])
        self.assertAlmostEqual(sweep["lines"]["L1_4"]["current_pu"], 0.6, delta=0.03)
        
        # Verify thermal convection: L4_5 temperature > L1_4 temperature (due to current 1.2 > 0.6)
        self.assertGreater(sweep["lines"]["L4_5"]["temperature_c"], sweep["lines"]["L1_4"]["temperature_c"])
        
    def test_calibration_drift(self):
        self.sensor.drift_enabled = True
        self.sensor.set_calibration_drift("bus_5_v", 0.05)
        
        sweep = self.sensor.simulate_sensor_sweep(self.mock_telemetry)
        # Bus 5 voltage should drift towards 1.00 + 0.05 = 1.05
        self.assertAlmostEqual(sweep["buses"]["Bus_5"]["voltage_pu"], 1.05, delta=0.02)
        
    def test_packet_loss(self):
        self.sensor.packet_loss_rate = 1.0
        sweep = self.sensor.simulate_sensor_sweep(self.mock_telemetry)
        self.assertEqual(sweep, {})

if __name__ == "__main__":
    unittest.main()
