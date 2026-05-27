import unittest
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from esp32_bridge import ESP32Bridge

from relay_controller import RelayController

class TestESP32Bridge(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = RelayController(self.mgr)
        self.bridge = ESP32Bridge(self.mgr, self.ctrl)
        
    def test_heartbeat_nominal(self):
        hb = self.bridge.run_heartbeat_cycle()
        self.assertEqual(hb["device_id"], "esp32")
        self.assertEqual(hb["status"], "ONLINE")
        self.assertTrue(10.0 <= hb["latency_ms"] <= 35.0)
        self.assertEqual(hb["trust"], 1.0)
        
    def test_gpio_write_success(self):
        # Open L4_5 (originally CLOSED=1)
        success = self.bridge.execute_gpio_write("pin_12", 0)
        self.assertTrue(success)
        self.assertEqual(self.mgr.gpio["pin_12"], 0)
        
        # Simulate time passing and update transitions to latch contacts
        import time
        time.sleep(0.2)
        self.ctrl.update_transitions()
        
        # Check relay coil and feedback state updated
        self.assertEqual(self.mgr.relays["L4_5"]["coil"], "OPEN")
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "OPEN")
        # Check feedback input pin updated (pin_12 + 17 = pin_29? No, in map pin_25 is L4_5 feedback)
        self.assertEqual(self.mgr.gpio["pin_25"], 0)
        
    def test_comms_failure(self):
        # Inject comms failure
        self.bridge.set_comms_failure(True)
        
        # Heartbeat returns OFFLINE
        hb = self.bridge.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "OFFLINE")
        self.assertEqual(hb["latency_ms"], -1.0)
        
        # GPIO write fails and trust is penalized
        success = self.bridge.execute_gpio_write("pin_12", 0)
        self.assertFalse(success)
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)
        
    def test_latency_spike(self):
        self.bridge.set_latency_spike(True)
        hb = self.bridge.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "ONLINE")
        self.assertTrue(250.0 <= hb["latency_ms"] <= 500.0)
        # Verify trust is penalized due to latency > 200ms
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)

if __name__ == "__main__":
    unittest.main()
