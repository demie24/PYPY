import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.redundancy_coordinator import RedundancyCoordinator

class TestRedundancyCoordinator(unittest.TestCase):
    def setUp(self):
        self.coordinator = RedundancyCoordinator()

    def test_initial_state(self):
        self.assertEqual(self.coordinator.redundancy_health["esp32_zone1"], 100.0)
        self.assertFalse(self.coordinator.redundant_execution_active)
        self.assertEqual(self.coordinator.failover_history, [])

    def test_evaluate_redundancy_health_nominal(self):
        fleet_status = {
            "fleet": {
                "esp32_zone1": {"status": "ONLINE", "latency_ms": 5.0, "trust": 1.0},
                "esp32_backup": {"status": "ONLINE", "latency_ms": 6.0, "trust": 1.0}
            }
        }
        timing_deviations = {
            "esp32_zone1": 2.0,
            "esp32_backup": 3.0
        }
        
        self.coordinator.evaluate_redundancy_health(fleet_status, timing_deviations)
        self.assertEqual(self.coordinator.redundancy_health["esp32_zone1"], 100.0)
        self.assertTrue(self.coordinator.active_backups_synchronized["esp32_backup"])

    def test_evaluate_redundancy_health_penalties(self):
        # 1. Primary quarantined (-50)
        # 2. Backup latency > 100ms (-10)
        # 3. Timing drift difference > 10ms (-15)
        # Expected health: 100 - 50 - 10 - 15 = 25.0
        fleet_status = {
            "fleet": {
                "esp32_zone1": {"status": "QUARANTINED", "latency_ms": 5.0, "trust": 1.0},
                "esp32_backup": {"status": "ONLINE", "latency_ms": 120.0, "trust": 1.0}
            }
        }
        timing_deviations = {
            "esp32_zone1": 1.0,
            "esp32_backup": 15.0  # diff is 14 > 10
        }

        self.coordinator.evaluate_redundancy_health(fleet_status, timing_deviations)
        self.assertEqual(self.coordinator.redundancy_health["esp32_zone1"], 25.0)

    def test_route_redundant_command(self):
        cmd = {"command": "OPEN", "target": "L4_9"}
        
        # Redundant routing disabled (default) -> no duplication
        routes = self.coordinator.route_redundant_command(cmd, "esp32_zone1")
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0], cmd)
        
        # Enable redundant execution -> command is duplicated to esp32_backup
        self.coordinator.redundant_execution_active = True
        routes2 = self.coordinator.route_redundant_command(cmd, "esp32_zone1")
        self.assertEqual(len(routes2), 2)
        self.assertEqual(routes2[0], cmd)
        self.assertEqual(routes2[1]["redundant_route"], "esp32_backup")
        self.assertEqual(routes2[1]["source"], "SAFETY_GUARD")

    def test_arbitrate_responses(self):
        # 1. Single routing mode arbitration
        success, reason = self.coordinator.arbitrate_responses(True, False, "esp32_zone1")
        self.assertTrue(success)
        self.assertIn("Single routing active", reason)

        # 2. Redundant routing mode: both success
        self.coordinator.redundant_execution_active = True
        success2, reason2 = self.coordinator.arbitrate_responses(True, True, "esp32_zone1")
        self.assertTrue(success2)
        
        # 3. Failover case: primary fails, backup succeeds
        success3, reason3 = self.coordinator.arbitrate_responses(False, True, "esp32_zone1")
        self.assertTrue(success3)
        self.assertEqual(len(self.coordinator.failover_history), 1)
        self.assertEqual(self.coordinator.failover_history[0]["primary"], "esp32_zone1")
        self.assertEqual(self.coordinator.failover_history[0]["status"], "FAILOVER_VALIDATED")

        # 4. Out of sync case: primary succeeds, backup fails
        success4, reason4 = self.coordinator.arbitrate_responses(True, False, "esp32_zone1")
        self.assertTrue(success4)
        self.assertFalse(self.coordinator.active_backups_synchronized["esp32_backup"])

if __name__ == "__main__":
    unittest.main()
