import unittest
import time
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager

class TestHardwareStateManager(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        
    def test_initial_state(self):
        all_states = self.mgr.get_all_states()
        self.assertIn("esp32", all_states["devices"])
        self.assertIn("plc", all_states["devices"])
        self.assertEqual(all_states["devices"]["esp32"]["trust"], 1.0)
        self.assertEqual(all_states["devices"]["plc"]["trust"], 1.0)
        self.assertEqual(all_states["relays"]["L7_8"]["coil"], "OPEN")
        
    def test_trust_decay_recovery(self):
        # Decay trust
        self.mgr.decay_trust("esp32", 0.3)
        self.assertEqual(self.mgr.devices["esp32"]["trust"], 0.7)
        
        # Clamp minimum trust to 0.1
        self.mgr.decay_trust("esp32", 0.8)
        self.assertEqual(self.mgr.devices["esp32"]["trust"], 0.1)
        
        # Recover trust
        self.mgr.recover_trust("esp32", 0.4)
        self.assertEqual(self.mgr.devices["esp32"]["trust"], 0.5)
        
        # Clamp maximum trust to 1.0
        self.mgr.recover_trust("esp32", 0.9)
        self.assertEqual(self.mgr.devices["esp32"]["trust"], 1.0)
        
    def test_relay_discrepancy(self):
        # Perfect alignment: no penalty
        self.mgr.update_relay_state("L4_5", "CLOSED", "CLOSED")
        self.assertEqual(self.mgr.devices["esp32"]["trust"], 1.0)
        
        # Discrepancy on ESP32 controlled breaker: decays esp32 trust
        self.mgr.update_relay_state("L4_5", "CLOSED", "OPEN")
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)
        self.assertEqual(self.mgr.devices["plc"]["trust"], 1.0)
        
        # Discrepancy on PLC controlled breaker: decays plc trust
        self.mgr.update_relay_state("L7_8", "CLOSED", "OPEN")
        self.assertLess(self.mgr.devices["plc"]["trust"], 1.0)
        
    def test_device_timeouts(self):
        # Set last_seen back in time > 5.0 seconds
        self.mgr.devices["esp32"]["last_seen"] = time.time() - 6.0
        
        # Check timeouts updates health
        health = self.mgr.get_device_health()
        self.assertEqual(health["devices"]["esp32"]["status"], "OFFLINE")
        self.assertEqual(health["devices"]["esp32"]["latency_ms"], -1.0)
        self.assertLess(health["devices"]["esp32"]["trust"], 1.0)
        
    def test_update_heartbeat(self):
        # Nominal heartbeat
        self.mgr.update_device_heartbeat("esp32", 15.0)
        self.assertEqual(self.mgr.devices["esp32"]["status"], "ONLINE")
        self.assertEqual(self.mgr.devices["esp32"]["latency_ms"], 15.0)
        self.assertEqual(self.mgr.devices["esp32"]["trust"], 1.0)
        
        # High latency heartbeat: trust decays
        self.mgr.devices["esp32"]["trust"] = 1.0
        self.mgr.update_device_heartbeat("esp32", 250.0)
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)

if __name__ == "__main__":
    unittest.main()
