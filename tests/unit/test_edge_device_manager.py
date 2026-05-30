import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.edge_device_manager import EdgeDeviceManager

class TestEdgeDeviceManager(unittest.TestCase):
    def setUp(self):
        self.state_mgr = HardwareStateManager()
        self.mgr = EdgeDeviceManager(self.state_mgr)
        
    def test_fleet_initialization(self):
        self.assertIn("esp32_zone1", self.mgr.fleet)
        self.assertEqual(self.mgr.fleet["esp32_backup"]["role"], "STANDBY")
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["status"], "ONLINE")
        
    def test_heartbeat_updates_status(self):
        self.mgr.fleet["esp32_zone1"]["status"] = "OFFLINE"
        self.mgr.update_device_heartbeat("esp32_zone1", 12.5)
        
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["status"], "ONLINE")
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["latency_ms"], 12.5)
        
    def test_failover_routing(self):
        # Mapped breakers initially routed to primary
        dev_id, mode = self.mgr.get_controlling_device("L1_4")
        self.assertEqual(dev_id, "esp32_zone1")
        self.assertEqual(mode, "PRIMARY")
        
        # Primary goes offline
        self.mgr.fleet["esp32_zone1"]["status"] = "OFFLINE"
        
        # Should now route to backup ESP32
        dev_id, mode = self.mgr.get_controlling_device("L1_4")
        self.assertEqual(dev_id, "esp32_backup")
        self.assertEqual(mode, "FAILOVER")
        
        # If backup is also offline, it fails over to primary PLC (last resort)
        self.mgr.fleet["esp32_backup"]["status"] = "OFFLINE"
        dev_id, mode = self.mgr.get_controlling_device("L1_4")
        self.assertEqual(dev_id, "plc_primary")
        self.assertEqual(mode, "FAILOVER")

    def test_quarantine_updates(self):
        self.mgr.set_device_quarantine("esp32_zone1", True)
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["status"], "QUARANTINED")
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["trust"], 0.1)
        
        # Active failover routing is triggered automatically
        dev_id, mode = self.mgr.get_controlling_device("L1_4")
        self.assertEqual(dev_id, "esp32_backup")
        
        # Release quarantine
        self.mgr.set_device_quarantine("esp32_zone1", False)
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["status"], "ONLINE")
        self.assertEqual(self.mgr.fleet["esp32_zone1"]["trust"], 0.5)

    def test_aggregated_trust(self):
        # Initially, all are 1.0
        self.assertEqual(self.mgr.get_fleet_trust(), 1.0)
        
        # Degrade one primary trust
        self.mgr.fleet["esp32_zone1"]["trust"] = 0.4
        self.assertEqual(self.mgr.get_fleet_trust(), 0.85)

if __name__ == "__main__":
    unittest.main()
