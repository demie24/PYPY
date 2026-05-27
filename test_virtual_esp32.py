import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from virtual_esp32 import VirtualESP32
from virtual_relay_faults import VirtualRelayFaults

class TestVirtualESP32(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = VirtualRelayFaults(self.mgr)
        self.esp = VirtualESP32(self.mgr, self.ctrl)
        
    def test_nominal_behavior(self):
        hb = self.esp.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "ONLINE")
        self.assertTrue(self.esp.is_connected)
        self.assertEqual(self.esp.packet_drop_rate, 0.0)
        
    def test_heartbeat_failure_injection(self):
        self.esp.set_heartbeat_failure(True)
        self.assertTrue(self.esp.heartbeat_failure)
        hb = self.esp.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "OFFLINE")
        # Trust decay checks
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)
        
    def test_packet_drop_simulation(self):
        self.esp.set_packet_drop_rate(1.0) # Drop all packets
        success = self.esp.execute_gpio_write("pin_12", 0)
        self.assertFalse(success)
        self.assertLess(self.mgr.devices["esp32"]["trust"], 1.0)
        
    def test_stateful_reconnect_logic(self):
        # 1. Trigger DoS comms failure
        self.esp.set_comms_failure(True)
        self.assertFalse(self.esp.is_connected)
        self.assertEqual(self.esp.run_heartbeat_cycle()["status"], "OFFLINE")
        
        # 2. Clear DoS comms failure -> Schedules reconnection
        self.esp.reconnect_duration = 0.5 # Fast reconnect for test
        self.esp.set_comms_failure(False)
        self.assertFalse(self.esp.is_connected)
        self.assertGreater(self.esp.reconnect_time, 0.0)
        self.assertEqual(self.esp.run_heartbeat_cycle()["status"], "OFFLINE")
        
        # 3. Wait reconnect duration
        time.sleep(0.6)
        hb = self.esp.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "ONLINE")
        self.assertTrue(self.esp.is_connected)
        
    def test_telemetry_payload(self):
        payload = self.esp.get_telemetry_payload()
        self.assertIn("is_connected", payload)
        self.assertIn("packet_drop_rate", payload)
        self.assertIn("heartbeat_failure", payload)
        self.assertIn("reconnect_time_left", payload)

if __name__ == "__main__":
    unittest.main()
