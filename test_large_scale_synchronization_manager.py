import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from large_scale_synchronization_manager import LargeScaleSynchronizationManager

class TestLargeScaleSynchronizationManager(unittest.TestCase):
    def setUp(self):
        self.manager = LargeScaleSynchronizationManager()

    def test_initial_state(self):
        self.assertTrue(self.manager.sync_stabilized)
        self.assertEqual(self.manager.load_balance_factor, 0.1)
        self.assertFalse(self.manager.congestion_detected)
        self.assertEqual(self.manager.recovery_attempts, 0)
        self.assertEqual(self.manager.sync_interval_ms, 100.0)

    def test_monitor_nominal_drifts(self):
        self.manager.sync_interval_ms = 300.0
        drifts = {
            "esp32_zone1": 2.5,
            "esp32_zone2": -4.0,
            "esp32_zone3": 1.0,
            "plc_primary": 5.0
        }
        
        stabilized = self.manager.monitor_and_stabilize(drifts)
        
        self.assertTrue(stabilized)
        self.assertTrue(self.manager.sync_stabilized)
        self.assertEqual(self.manager.timing_deviations["esp32_zone1"], 2.5)
        self.assertEqual(self.manager.multi_zone_offsets["zone_2"], -4.0)
        self.assertFalse(self.manager.congestion_detected)

    def test_monitor_drift_exceeds_tolerance_warning(self):
        drifts = {
            "esp32_zone1": 18.0,  # exceeds 15.0ms drift warning
            "esp32_zone2": -2.0
        }
        
        stabilized = self.manager.monitor_and_stabilize(drifts)
        
        self.assertFalse(stabilized)
        self.assertFalse(self.manager.sync_stabilized)
        # Note: it's not recovery yet because drift <= 25.0ms
        self.assertEqual(self.manager.recovery_attempts, 0)

    def test_monitor_congestion_prevention(self):
        # Triggering traffic density / polling congestion
        # By setting sync_interval_ms to very low, we increase base_traffic calculation:
        # base_traffic = (active_devices_count * 5.0) / (self.sync_interval_ms / 10.0)
        # Let's use 6 active devices with drift and a small interval
        self.manager.sync_interval_ms = 20.0
        drifts = {
            "esp32_zone1": 2.0,
            "esp32_zone2": 1.5,
            "esp32_zone3": 2.2,
            "plc_primary": 1.8,
            "esp32_backup": 3.0,
            "plc_backup": 1.1
        }
        
        self.manager.monitor_and_stabilize(drifts)
        
        # load_balance_factor = (6 * 5) / (20 / 10) = 30 / 2 = 15.0 -> capped to 1.0
        self.assertEqual(self.manager.load_balance_factor, 1.0)
        self.assertTrue(self.manager.congestion_detected)
        # Dynamic sync interval should have been throttled (increased by 50)
        self.assertEqual(self.manager.sync_interval_ms, 70.0)

    def test_timing_recovery_recovery_loop(self):
        # Set a massive drift (> 25.0ms) to trigger NTP/PTP timing recovery
        drifts = {
            "esp32_zone1": 28.5,  # > 25.0ms
            "esp32_zone2": 1.0
        }
        
        stabilized = self.manager.monitor_and_stabilize(drifts)
        
        self.assertFalse(stabilized)
        self.assertEqual(self.manager.recovery_attempts, 1)
        # After recovery, timing deviation should settle to 1.2ms nominal jitter
        self.assertEqual(self.manager.timing_deviations["esp32_zone1"], 1.2)
        self.assertEqual(drifts["esp32_zone1"], 1.2)

if __name__ == "__main__":
    unittest.main()
