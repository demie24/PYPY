import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from physical_telemetry_validator import PhysicalTelemetryValidator

class TestPhysicalTelemetryValidator(unittest.TestCase):
    def setUp(self):
        self.validator = PhysicalTelemetryValidator()

    def test_empty_payload(self):
        is_valid, score, alerts = self.validator.validate_telemetry_integrity({}, {})
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)
        self.assertIn("EMPTY_TELEMETRY_PAYLOAD", alerts)

    def test_nominal_validation(self):
        telemetry = {
            "sensors": {
                "bus_1_v": 1.0,
                "line_L1_4_i": 0.5,
                "line_L1_4_temp": 40.0
            }
        }
        relays = {
            "L1_4": {"feedback": "CLOSED"}
        }
        is_valid, score, alerts = self.validator.validate_telemetry_integrity(telemetry, relays)
        self.assertTrue(is_valid)
        self.assertEqual(score, 100.0)
        self.assertEqual(len(alerts), 0)

    def test_out_of_bounds_checks(self):
        telemetry = {
            "sensors": {
                "bus_1_v": -0.5,       # Under limit
                "line_L1_4_i": 4.5,     # Over limit
                "line_L1_4_temp": 150.0 # Over limit
            }
        }
        is_valid, score, alerts = self.validator.validate_telemetry_integrity(telemetry, {})
        self.assertFalse(is_valid)
        self.assertLess(score, 100.0)
        self.assertTrue(any("VOLTAGE" in a for a in alerts))
        self.assertTrue(any("CURRENT" in a for a in alerts))
        self.assertTrue(any("TEMPERATURE" in a for a in alerts))

    def test_breaker_desync(self):
        telemetry = {
            "sensors": {
                "line_L1_4_i": 0.8  # Current is flowing
            }
        }
        relays = {
            "L1_4": {"feedback": "OPEN"}  # But breaker feedback says OPEN
        }
        is_valid, score, alerts = self.validator.validate_telemetry_integrity(telemetry, relays)
        self.assertLess(score, 100.0)
        self.assertTrue(any("BREAKER_CURRENT_DESYNC" in a for a in alerts))

    def test_rate_of_change(self):
        # First tick: set initial history
        telemetry_1 = {
            "sensors": {
                "bus_1_v": 1.0
            }
        }
        self.validator.validate_telemetry_integrity(telemetry_1, {})

        # Second tick: sudden huge voltage drop (from 1.0 to 0.2)
        telemetry_2 = {
            "sensors": {
                "bus_1_v": 0.2
            }
        }
        is_valid, score, alerts = self.validator.validate_telemetry_integrity(telemetry_2, {})
        self.assertLess(score, 100.0)
        self.assertTrue(any("IMPOSSIBLE_RATE_OF_CHANGE" in a for a in alerts))

    def test_stale_sensor_detection(self):
        # Run 10 ticks with identical telemetry
        telemetry = {
            "sensors": {
                "bus_1_v": 1.0,
                "line_L1_4_i": 0.5
            }
        }
        
        for i in range(9):
            self.validator.validate_telemetry_integrity(telemetry, {})
            
        # 10th tick should trigger staleness
        is_valid, score, alerts = self.validator.validate_telemetry_integrity(telemetry, {})
        self.assertLess(score, 100.0)
        self.assertTrue(any("STALE_SENSOR" in a for a in alerts))

if __name__ == "__main__":
    unittest.main()
