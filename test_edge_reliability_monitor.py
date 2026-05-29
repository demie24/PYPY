import unittest
import sys
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from edge_reliability_monitor import EdgeReliabilityMonitor

class TestEdgeReliabilityMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = EdgeReliabilityMonitor()

    def test_initial_state(self):
        self.assertEqual(self.monitor.reliability_scores["esp32_zone1"], 1.0)
        self.assertFalse(self.monitor.lockout_states["esp32_zone1"])
        self.assertEqual(len(self.monitor.alerts), 0)

    def test_reliability_decay_and_recovery(self):
        # Decay
        self.monitor.decay_reliability("esp32_zone1", 0.2)
        self.assertEqual(self.monitor.reliability_scores["esp32_zone1"], 0.8)

        # Recover
        self.monitor.recover_reliability("esp32_zone1", 0.05)
        self.assertEqual(self.monitor.reliability_scores["esp32_zone1"], 0.85)

        # Capped at 1.0
        self.monitor.recover_reliability("esp32_zone1", 0.5)
        self.assertEqual(self.monitor.reliability_scores["esp32_zone1"], 1.0)

        # Locked at 0.0 minimum
        self.monitor.decay_reliability("esp32_zone1", 2.0)
        self.assertEqual(self.monitor.reliability_scores["esp32_zone1"], 0.0)

    def test_relay_timeout_tracking(self):
        # Register command to OPEN relay L1_4 on device esp32_zone1
        self.monitor.register_relay_command("L1_4", "OPEN", "esp32_zone1")
        self.assertEqual(len(self.monitor.pending_relay_commands), 1)

        # Success transition within 200ms -> removed from tracking
        fleet_data = {"fleet": {}}
        relay_telemetry = {"relays": {"L1_4": {"feedback": "OPEN"}}}
        self.monitor.tick(fleet_data, relay_telemetry)
        self.assertEqual(len(self.monitor.pending_relay_commands), 0)

        # Timeout scenario
        self.monitor.register_relay_command("L2_7", "CLOSED", "esp32_zone1")
        
        # Simulate elapsed time > 200ms by retroactively modifying registration time
        self.monitor.pending_relay_commands["L2_7"]["timestamp"] = time.time() - 0.25
        
        # Check telemetry with no transition (still OPEN)
        relay_telemetry = {"relays": {"L2_7": {"feedback": "OPEN"}}}
        self.monitor.tick(fleet_data, relay_telemetry)
        
        self.assertEqual(len(self.monitor.pending_relay_commands), 1)
        self.assertTrue(any("RELAY_TIMEOUT" in a for a in self.monitor.alerts))
        self.assertLess(self.monitor.reliability_scores["esp32_zone1"], 1.0)

    def test_interface_flapping_lockout(self):
        # Simulate status transitions: ONLINE -> OFFLINE -> ONLINE -> OFFLINE -> ONLINE within 15s
        self.monitor.update_device_status("esp32_zone1", "OFFLINE")
        self.monitor.update_device_status("esp32_zone1", "ONLINE")
        self.monitor.update_device_status("esp32_zone1", "OFFLINE")
        self.monitor.update_device_status("esp32_zone1", "ONLINE") # 4th transition

        self.assertTrue(self.monitor.lockout_states["esp32_zone1"])
        self.assertTrue(any("INTERFACE_FLAPPING_LOCKOUT" in a for a in self.monitor.alerts))
        self.assertLess(self.monitor.reliability_scores["esp32_zone1"], 1.0)

        # Locked out devices cannot recover reliability score
        prev_score = self.monitor.reliability_scores["esp32_zone1"]
        self.monitor.recover_reliability("esp32_zone1", 0.1)
        self.assertEqual(self.monitor.reliability_scores["esp32_zone1"], prev_score)

        # Locked out devices can recover after cooldown ticks (simulate 30s elapsed)
        self.monitor.lockout_times["esp32_zone1"] = time.time() - 31.0
        self.monitor.tick({"fleet": {"esp32_zone1": {"status": "ONLINE", "latency_ms": 10.0}}}, {"relays": {}})
        self.assertFalse(self.monitor.lockout_states["esp32_zone1"])
        self.assertTrue(any("INTERFACE_LOCKOUT_RELEASED" in a for a in self.monitor.alerts))

if __name__ == "__main__":
    unittest.main()
