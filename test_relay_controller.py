import unittest
import time
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from relay_controller import RelayController

class TestRelayController(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = RelayController(self.mgr)
        
    def test_switching_success(self):
        # Open L4_5 (nominally CLOSED)
        success, msg = self.ctrl.trigger_switching("L4_5", "OPEN")
        self.assertTrue(success)
        
        # Coil changes instantly
        self.assertEqual(self.mgr.relays["L4_5"]["coil"], "OPEN")
        # Contact feedback does not change instantly (physical delay)
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "CLOSED")
        
    def test_anti_chattering_lockout(self):
        # First switch works
        success1, msg1 = self.ctrl.trigger_switching("L4_5", "OPEN")
        self.assertTrue(success1)
        
        # Second immediate switch is blocked
        success2, msg2 = self.ctrl.trigger_switching("L4_5", "CLOSED")
        self.assertFalse(success2)
        self.assertIn("lockout", msg2)
        # Trust is penalized
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)
        self.assertLess(self.mgr.devices["plc"]["trust"], 1.0)
        
    def test_contact_bounce_and_latch(self):
        self.ctrl.trigger_switching("L4_5", "OPEN")
        
        # 1. Update during early transition (feedback should remain OLD state, e.g. CLOSED)
        self.ctrl.active_transitions["L4_5"]["start_time"] = time.time() - 0.05
        self.ctrl.update_transitions()
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "CLOSED")
        
        # 2. Update during bounce phase (random OPEN/CLOSED feedback or toggling)
        self.ctrl.active_transitions["L4_5"]["start_time"] = time.time() - 0.12
        self.ctrl.update_transitions()
        self.assertIn(self.mgr.relays["L4_5"]["feedback"], ["OPEN", "CLOSED"])
        
        # 3. Update after transition duration: feedback must fully latch target
        self.ctrl.active_transitions["L4_5"]["start_time"] = time.time() - 0.20
        self.ctrl.update_transitions()
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "OPEN")
        self.assertNotIn("L4_5", self.ctrl.active_transitions)

if __name__ == "__main__":
    unittest.main()
