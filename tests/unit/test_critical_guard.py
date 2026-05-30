import unittest
import sys
import os

# Setup import paths

from core.self_healing.critical_infrastructure_guard import CriticalInfrastructureGuard

class TestCriticalInfrastructureGuard(unittest.TestCase):
    def setUp(self):
        self.guard = CriticalInfrastructureGuard()

    def test_priority_selection(self):
        # All load buses are active
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 1.0},
                    "Bus_6": {"voltage_pu": 1.0},
                    "Bus_8": {"voltage_pu": 1.0}
                }
            }
        }
        # Available loads to select from
        available = ["Bus_5", "Bus_8", "Bus_6"]
        # Lowest priority (highest number) is Bus_6 (priority 3) -> should select Bus_6 first to shed
        selected = self.guard.select_load_to_shed(available, telemetry)
        self.assertEqual(selected, "Bus_6")

    def test_gated_redirection(self):
        # Try to shed critical Bus_5 when Bus_6 is still powered
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 1.0},
                    "Bus_6": {"voltage_pu": 1.0},
                    "Bus_8": {"voltage_pu": 1.0}
                }
            }
        }
        approved, reason, modified_cmd = self.guard.gate_load_shed_command("Bus_5", 25.0, telemetry)
        
        # Should be rejected/redirected
        self.assertFalse(approved)
        self.assertIn("Redirected", reason)
        # Verify it redirected target to Bus_6
        self.assertEqual(modified_cmd["target"], "Bus_6")

if __name__ == "__main__":
    unittest.main()
