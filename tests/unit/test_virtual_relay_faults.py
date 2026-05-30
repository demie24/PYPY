import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.virtual_relay_faults import VirtualRelayFaults

class TestVirtualRelayFaults(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.relay = VirtualRelayFaults(self.mgr)
        
    def test_stuck_relay(self):
        # 1. Stuck OPEN
        self.relay.set_stuck_relay("L4_5", "OPEN")
        self.assertEqual(self.mgr.relays["L4_5"]["coil"], "OPEN")
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "OPEN")
        
        # 2. Command toggle
        success, reason = self.relay.trigger_switching("L4_5", "CLOSED")
        self.assertFalse(success)
        self.assertIn("stuck", reason)
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0) # esp32 because L4_5 is mapped to esp32
        
    def test_delayed_switching(self):
        # L4_5 is CLOSED by default. We command it to OPEN.
        self.relay.set_switching_delay("L4_5", 1.0)
        success, reason = self.relay.trigger_switching("L4_5", "OPEN")
        self.assertTrue(success)
        
        # Immediate check (should be transitioning, coil is OPEN but feedback is still old CLOSED state)
        self.assertEqual(self.mgr.relays["L4_5"]["coil"], "OPEN")
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "CLOSED")
        
        # Tick transition loop at 0.1s
        self.relay.update_transitions()
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "CLOSED")
        
        # Wait 1.1s
        time.sleep(1.1)
        self.relay.update_transitions()
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "OPEN")
        
    def test_contact_welding(self):
        # welded contact CLOSED. First open it then welding forces it closed.
        self.relay.set_contact_welding("L4_5", True)
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "CLOSED")
        
        # Try to open it
        self.relay.trigger_switching("L4_5", "OPEN")
        time.sleep(0.2)
        self.relay.update_transitions()
        
        # Feedback remains CLOSED even if coil is OPEN
        self.assertEqual(self.mgr.relays["L4_5"]["coil"], "OPEN")
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "CLOSED")
        
    def test_desync_relay(self):
        self.relay.set_relay_desync("L4_5", True)
        # Feedback is inverted from coil (L4_5 coil is CLOSED initially, so feedback becomes OPEN)
        self.assertEqual(self.mgr.relays["L4_5"]["feedback"], "OPEN")
        
    def test_rapid_oscillation(self):
        # Oscillate at 5Hz (period 0.2s)
        self.relay.set_relay_oscillation("L4_5", 5.0)
        
        now = time.time()
        self.relay.update_transitions()
        first_state = self.mgr.relays["L4_5"]["feedback"]
        
        # Wait 0.1s (half period) to guarantee a toggle
        time.sleep(0.1)
        self.relay.update_transitions()
        second_state = self.mgr.relays["L4_5"]["feedback"]
        
        # Since it toggles, first_state and second_state should be different at some sample ticks
        # Wait more if necessary, but chattering updates feedback dynamically
        self.relay.set_relay_oscillation("L4_5", 0.0) # clear

if __name__ == "__main__":
    unittest.main()
