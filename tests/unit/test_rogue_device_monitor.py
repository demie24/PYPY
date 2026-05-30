import unittest
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.rogue_device_monitor import RogueDeviceMonitor

class TestRogueDeviceMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = RogueDeviceMonitor()
        
    def test_nominal_state(self):
        self.assertEqual(self.monitor.hardware_trust_score, 1.0)
        devices = self.monitor.get_devices_status()
        self.assertEqual(len(devices), 2)
        for dev in devices:
            self.assertTrue(dev["trusted"])
            
    def test_authorized_insertion(self):
        # Insert STM32 Virtual COM port again (already connected)
        success = self.monitor.simulate_device_insertion("0483", "5740", "STM32 Virtual COM Port")
        self.assertTrue(success)
        self.assertEqual(self.monitor.hardware_trust_score, 1.0)
        self.assertEqual(len(self.monitor.connected_devices), 2)
        
    def test_rogue_device_insertion_and_removal(self):
        # Insert unauthorized USB key
        success = self.monitor.simulate_device_insertion("16c0", "05df", "Rogue Rubber Ducky")
        self.assertFalse(success)
        self.assertLess(self.monitor.hardware_trust_score, 1.0)
        self.assertEqual(round(self.monitor.hardware_trust_score, 1), 0.7)
        self.assertEqual(len(self.monitor.connected_devices), 3)
        
        # Check trust payload
        payload = self.monitor.get_trust_payload()
        self.assertEqual(payload["unauthorized_count"], 1)
        self.assertEqual(payload["total_devices"], 3)
        self.assertEqual(payload["trust_score"], 0.7)
        
        # Remove rogue device
        self.monitor.simulate_device_removal("16c0", "05df")
        self.assertEqual(self.monitor.hardware_trust_score, 1.0)
        self.assertEqual(len(self.monitor.connected_devices), 2)
        
    def test_reset(self):
        self.monitor.simulate_device_insertion("16c0", "05df", "Rogue Rubber Ducky")
        self.monitor.reset()
        self.assertEqual(self.monitor.hardware_trust_score, 1.0)
        self.assertEqual(len(self.monitor.connected_devices), 2)

if __name__ == "__main__":
    unittest.main()
