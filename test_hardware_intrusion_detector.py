import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_intrusion_detector import HardwareIntrusionDetector

class TestHardwareIntrusionDetector(unittest.TestCase):
    def setUp(self):
        self.detector = HardwareIntrusionDetector()
        
    def test_nominal_state(self):
        self.assertEqual(self.detector.intrusion_score, 0.0)
        self.assertEqual(len(self.detector.alerts), 0)
        
    def test_unauthorized_command_source(self):
        # Whitelisted source (nominal)
        success = self.detector.analyze_command("CLOSE", "L1_4", "FLISR")
        self.assertTrue(success)
        self.assertEqual(self.detector.intrusion_score, 0.0)
        
        # Non-whitelisted source (unauthorized)
        success = self.detector.analyze_command("CLOSE", "L7_8", "MALICIOUS_USB_HOST")
        self.assertFalse(success)
        self.assertEqual(self.detector.intrusion_score, 40.0)
        self.assertEqual(len(self.detector.alerts), 1)
        self.assertEqual(self.detector.alerts[-1]["alert_type"], "UNAUTHORIZED_COMMAND_ORIGIN")
        
    def test_command_chattering_rate_limit(self):
        # Send 3 commands in rapid succession (within 5 seconds)
        self.detector.analyze_command("OPEN", "L1_4", "FLISR")
        self.detector.analyze_command("CLOSE", "L1_4", "FLISR")
        
        # 3rd command triggers chattering flood alert
        success = self.detector.analyze_command("OPEN", "L1_4", "FLISR")
        self.assertFalse(success)
        self.assertEqual(self.detector.intrusion_score, 25.0)
        self.assertEqual(self.detector.alerts[-1]["alert_type"], "CHATTERING_COMMAND_FLOOD")
        
    def test_telemetry_tampering_fdia(self):
        # Tiny difference -> no alert
        self.detector.analyze_telemetry("bus_5_v", 1.0, 1.02)
        self.assertEqual(self.detector.intrusion_score, 0.0)
        
        # Suspiciously high raw vs estimated difference -> FDIA alert
        self.detector.analyze_telemetry("bus_5_v", 1.0, 0.8)
        self.assertEqual(self.detector.intrusion_score, 15.0)
        self.assertEqual(self.detector.alerts[-1]["alert_type"], "TELEMETRY_TAMPERING_FDIA")
        
    def test_reset(self):
        self.detector.analyze_command("CLOSE", "L7_8", "MALICIOUS_USB_HOST")
        self.detector.reset()
        self.assertEqual(self.detector.intrusion_score, 0.0)
        self.assertEqual(len(self.detector.alerts), 0)

if __name__ == "__main__":
    unittest.main()
