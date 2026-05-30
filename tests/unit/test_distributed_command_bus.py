import unittest
import sys
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.distributed_command_bus import DistributedCommandBus

class TestDistributedCommandBus(unittest.TestCase):
    def setUp(self):
        self.bus = DistributedCommandBus()
        
    def test_send_command_queues_message(self):
        cmd = {"command": "CLOSE", "target": "L1_4", "source": "SCADA"}
        tx_id = "test_tx_01"
        self.bus.send_command(tx_id, cmd, "esp32_zone1", 20.0)
        
        self.assertIn(tx_id, self.bus.pending_transmissions)
        self.assertEqual(self.bus.pending_transmissions[tx_id]["status"], "PENDING")
        self.assertEqual(self.bus.transmitted_count, 1)

    def test_bus_processing_delivery(self):
        cmd = {"command": "CLOSE", "target": "L1_4", "source": "SCADA"}
        tx_id = "test_tx_02"
        # base latency 0.0 to execute instantly on next tick
        self.bus.send_command(tx_id, cmd, "esp32_zone1", 0.0)
        
        # Callback returns device manager health status mock
        mock_dev_mgr = lambda dev: {"status": "ONLINE", "trust": 1.0}
        
        delivered = self.bus.process_bus_tick(mock_dev_mgr)
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0][0], tx_id)
        self.assertEqual(delivered[0][1], cmd)
        self.assertEqual(self.bus.pending_transmissions[tx_id]["status"], "DELIVERED")

    def test_bus_delivery_offline_device(self):
        cmd = {"command": "CLOSE", "target": "L1_4", "source": "SCADA"}
        tx_id = "test_tx_03"
        self.bus.send_command(tx_id, cmd, "esp32_zone1", 0.0)
        
        # Device is offline
        mock_dev_mgr = lambda dev: {"status": "OFFLINE", "trust": 1.0}
        
        delivered = self.bus.process_bus_tick(mock_dev_mgr)
        self.assertEqual(len(delivered), 0)
        self.assertNotIn(tx_id, self.bus.pending_transmissions) # Archived as NACKED
        self.assertEqual(self.bus.history[-1]["status"], "NACKED")

    def test_command_acknowledgement(self):
        cmd = {"command": "CLOSE", "target": "L1_4", "source": "SCADA"}
        tx_id = "test_tx_04"
        self.bus.send_command(tx_id, cmd, "esp32_zone1", 0.0)
        
        self.bus.acknowledge_command(tx_id, success=True, reason="Execution complete")
        self.assertNotIn(tx_id, self.bus.pending_transmissions)
        self.assertEqual(self.bus.history[-1]["status"], "ACKED")
        self.assertEqual(self.bus.history[-1]["details"], "Execution complete")

if __name__ == "__main__":
    unittest.main()
