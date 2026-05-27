import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from self_preservation_policy_engine import SelfPreservationPolicyEngine

class TestSelfPreservationPolicy(unittest.TestCase):
    def setUp(self):
        self.engine = SelfPreservationPolicyEngine()

    def test_no_telemetry(self):
        res = self.engine.evaluate_policy(None, {})
        self.assertEqual(res["active_policy"], "NOMINAL")
        self.assertEqual(res["preservation_rules"], [])
        self.assertEqual(res["proactive_commands"], [])

    def test_policy_transitions(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_6": {"P_mw": 50.0},
                    "Bus_8": {"P_mw": 50.0}
                }
            }
        }

        # 1. NOMINAL
        res = self.engine.evaluate_policy(telemetry, {"collapse_probability": 5.0, "survivability_horizon": 999.0})
        self.assertEqual(res["active_policy"], "NOMINAL")
        self.assertEqual(self.engine.active_policy, "NOMINAL")
        self.assertEqual(len(res["proactive_commands"]), 0)

        # 2. PREVENTATIVE
        res = self.engine.evaluate_policy(telemetry, {"collapse_probability": 20.0, "survivability_horizon": 50.0})
        self.assertEqual(res["active_policy"], "PREVENTATIVE")
        self.assertEqual(len(res["proactive_commands"]), 0)

        # 3. SELF_PRESERVATION (triggers Bus 6 shedding)
        res = self.engine.evaluate_policy(telemetry, {"collapse_probability": 45.0, "survivability_horizon": 25.0})
        self.assertEqual(res["active_policy"], "SELF_PRESERVATION")
        self.assertEqual(len(res["proactive_commands"]), 1)
        self.assertEqual(res["proactive_commands"][0]["command"], "SHED_LOAD")
        self.assertEqual(res["proactive_commands"][0]["target"], "Bus_6")
        self.assertEqual(res["proactive_commands"][0]["percentage"], 25.0)

        # 4. Statefulness check: second call in SELF_PRESERVATION shouldn't shed Bus 6 again
        res2 = self.engine.evaluate_policy(telemetry, {"collapse_probability": 45.0, "survivability_horizon": 25.0})
        self.assertEqual(len(res2["proactive_commands"]), 0)

        # 5. EMERGENCY_DEGRADATION (triggers Bus 8 shedding since Bus 6 is already in history)
        res3 = self.engine.evaluate_policy(telemetry, {"collapse_probability": 80.0, "survivability_horizon": 8.0})
        self.assertEqual(res3["active_policy"], "EMERGENCY_DEGRADATION")
        self.assertEqual(len(res3["proactive_commands"]), 1)
        self.assertEqual(res3["proactive_commands"][0]["target"], "Bus_8")
        self.assertEqual(res3["proactive_commands"][0]["percentage"], 30.0)

        # 6. Reset to NOMINAL clears history
        res4 = self.engine.evaluate_policy(telemetry, {"collapse_probability": 0.0, "survivability_horizon": 999.0})
        self.assertEqual(res4["active_policy"], "NOMINAL")
        self.assertEqual(len(self.engine.proactive_shed_history), 0)

if __name__ == "__main__":
    unittest.main()
