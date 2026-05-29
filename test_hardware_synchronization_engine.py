import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_synchronization_engine import HardwareSynchronizationEngine

class TestHardwareSynchronizationEngine(unittest.TestCase):
    def setUp(self):
        self.sync = HardwareSynchronizationEngine()
        
    def test_clock_ticking_and_drift(self):
        self.assertEqual(self.sync.tick_counter, 0)
        self.sync.tick()
        self.assertEqual(self.sync.tick_counter, 1)
        
        # Drifts should accumulate
        self.assertGreater(self.sync.device_drifts["esp32_zone1"], 0.0)
        self.assertGreater(self.sync.device_drifts["plc_primary"], 0.0)
        
    def test_device_clock_sync(self):
        self.sync.tick()
        self.sync.tick()
        drift = self.sync.device_drifts["esp32_zone1"]
        self.assertGreater(drift, 0.0)
        
        old_drift = self.sync.sync_device_clock("esp32_zone1")
        self.assertEqual(old_drift, drift)
        self.assertEqual(self.sync.device_drifts["esp32_zone1"], 0.0)

    def test_telemetry_buffering(self):
        dummy_state = {"L1_4": "CLOSED"}
        self.sync.record_telemetry_state(10, "esp32_zone1", dummy_state)
        
        aligned = self.sync.get_aligned_telemetry(10)
        self.assertIsNotNone(aligned)
        self.assertEqual(aligned["esp32_zone1"]["state"], dummy_state)
        
    def test_failover_alignment(self):
        state1 = {"relay": "CLOSED"}
        state2 = {"relay": "OPEN"}
        
        # Test misalignment
        self.sync.record_telemetry_state(self.sync.tick_counter, "esp32_zone1", state1)
        self.sync.record_telemetry_state(self.sync.tick_counter, "esp32_backup", state2)
        self.sync._verify_failover_alignment()
        self.assertFalse(self.sync.failover_aligned["esp32_zone1"])
        
        # Test alignment
        self.sync.replicate_state("esp32_zone1", "esp32_backup", state1)
        self.sync._verify_failover_alignment()
        self.assertTrue(self.sync.failover_aligned["esp32_zone1"])

if __name__ == "__main__":
    unittest.main()
