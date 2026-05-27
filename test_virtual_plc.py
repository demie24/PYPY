import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from virtual_plc import VirtualPLC
from virtual_relay_faults import VirtualRelayFaults

class TestVirtualPLC(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = VirtualRelayFaults(self.mgr)
        self.plc = VirtualPLC(self.mgr, self.ctrl)
        
    def test_nominal_behavior(self):
        self.assertTrue(self.plc.is_connected)
        hb = self.plc.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "ONLINE")
        
    def test_modbus_exception_handling(self):
        self.plc.set_modbus_exception_rate(1.0) # Always fail Modbus commands
        self.assertIsNone(self.plc.read_coils(1, 1))
        self.assertFalse(self.plc.write_single_coil(1, 1))
        self.assertLess(self.mgr.devices["plc"]["trust"], 1.0)
        
    def test_write_delay_queue(self):
        self.plc.set_write_delay(0.5)
        # Write to coil 8 (relays mapping: address 8 -> L7_8 which starts OPEN)
        success = self.plc.write_single_coil(8, 1) 
        self.assertTrue(success)
        
        # Check command is queued
        self.assertEqual(len(self.plc.write_queue), 1)
        self.assertEqual(self.mgr.relays["L7_8"]["coil"], "OPEN") # Not executed yet
        
        # Check queue processed after time passes
        time.sleep(0.6)
        self.plc.process_write_queue()
        self.assertEqual(len(self.plc.write_queue), 0)
        self.assertEqual(self.mgr.relays["L7_8"]["coil"], "CLOSED")
        
    def test_stateful_reconnect(self):
        self.plc.reconnect_duration = 0.5
        self.plc.set_comms_failure(True)
        self.assertFalse(self.plc.is_connected)
        self.assertEqual(self.plc.run_heartbeat_cycle()["status"], "OFFLINE")
        
        self.plc.set_comms_failure(False)
        self.assertFalse(self.plc.is_connected)
        time.sleep(0.6)
        
        hb = self.plc.run_heartbeat_cycle()
        self.assertEqual(hb["status"], "ONLINE")
        self.assertTrue(self.plc.is_connected)

if __name__ == "__main__":
    unittest.main()
