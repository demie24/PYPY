import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from autonomous_balancer import AutonomousBalancer

class MockGuard:
    def select_load_to_shed(self, available_loads, telemetry):
        # Always shed the first available load
        return available_loads[0] if available_loads else None

class TestAutonomousBalancer(unittest.TestCase):
    def setUp(self):
        self.balancer = AutonomousBalancer()
        self.guard = MockGuard()

    def test_nominal_balance(self):
        # Mismatch is 0 MW
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "is_gen": True, "P_mw": 100.0},
                    "Bus_5": {"voltage_pu": 1.0, "is_load": True, "P_mw": 100.0}
                }
            }
        }
        islands = [{
            "island_id": "ISLAND_1",
            "buses": ["Bus_1", "Bus_5"],
            "generators": ["Bus_1"],
            "loads": ["Bus_5"],
            "has_generation": True
        }]
        res = self.balancer.balance_grid(telemetry, islands, self.guard)
        self.assertEqual(res["mismatches"]["ISLAND_1"], 0.0)
        self.assertEqual(res["frequencies"]["ISLAND_1"], 60.0)
        self.assertEqual(len(res["balancing_commands"]), 0)

    def test_under_generation_shedding(self):
        # Generation = 50 MW, Load = 100 MW -> deficit = -50 MW
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "is_gen": True, "P_mw": 50.0},
                    "Bus_5": {"voltage_pu": 1.0, "is_load": True, "P_mw": 100.0}
                }
            }
        }
        islands = [{
            "island_id": "ISLAND_1",
            "buses": ["Bus_1", "Bus_5"],
            "generators": ["Bus_1"],
            "loads": ["Bus_5"],
            "has_generation": True
        }]
        # Run balancer multiple times to propagate frequency drop
        for _ in range(5):
            res = self.balancer.balance_grid(telemetry, islands, self.guard)

        # Mismatch should be negative
        self.assertEqual(res["mismatches"]["ISLAND_1"], -50.0)
        # Frequency should drop
        self.assertLess(res["frequencies"]["ISLAND_1"], 59.7)
        # Should recommend SHED_LOAD
        self.assertEqual(res["balancing_commands"][0]["command"], "SHED_LOAD")
        self.assertEqual(res["balancing_commands"][0]["target"], "Bus_5")

if __name__ == "__main__":
    unittest.main()
