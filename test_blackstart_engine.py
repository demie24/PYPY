import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from blackstart_engine import BlackstartEngine

class TestBlackstartEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BlackstartEngine()

    def test_complete_nominal(self):
        # Grid is healthy, blackstart is inactive (COMPLETE state)
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0},
                    "Bus_2": {"voltage_pu": 1.0},
                    "Bus_3": {"voltage_pu": 1.0}
                },
                "breakers": {}
            }
        }
        res = self.engine.evaluate_blackstart(telemetry)
        self.assertFalse(res["active_blackstart"])
        self.assertEqual(res["blackstart_state"], "COMPLETE")
        self.assertIsNone(res["recommended_command"])

    def test_blackstart_sequence(self):
        # 1. Trigger collapse (all voltages < 0.20)
        telemetry = {
            "state": {
                "buses": {f"Bus_{i+1}": {"voltage_pu": 0.0} for i in range(9)},
                "breakers": {lid: "OPEN" for lid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]}
            }
        }
        res = self.engine.evaluate_blackstart(telemetry)
        self.assertTrue(res["active_blackstart"])
        self.assertEqual(res["blackstart_state"], "COLLAPSED")
        # Should recommend starting generator on Bus_1
        self.assertEqual(res["recommended_command"]["command"], "START_GEN")
        self.assertEqual(res["recommended_command"]["target"], "Bus_1")

        # 2. Bus_1 starts up
        telemetry["state"]["buses"]["Bus_1"]["voltage_pu"] = 1.0
        self.engine.evaluate_blackstart(telemetry)
        res = self.engine.evaluate_blackstart(telemetry)
        # Check transition to START_MAIN_GEN (should recommend closing L1_4)
        self.assertEqual(res["blackstart_state"], "START_MAIN_GEN")
        self.assertEqual(res["recommended_command"]["command"], "CLOSE")
        self.assertEqual(res["recommended_command"]["target"], "L1_4")

        # 3. L1_4 closed, Bus_4 energized
        telemetry["state"]["breakers"]["L1_4"] = "CLOSED"
        telemetry["state"]["buses"]["Bus_4"] = {"voltage_pu": 1.0}
        self.engine.evaluate_blackstart(telemetry)
        res = self.engine.evaluate_blackstart(telemetry)
        # Check transition to ENERGIZE_PATH_1 (should recommend closing L4_9)
        self.assertEqual(res["blackstart_state"], "ENERGIZE_PATH_1")
        self.assertEqual(res["recommended_command"]["command"], "CLOSE")
        self.assertEqual(res["recommended_command"]["target"], "L4_9")

if __name__ == "__main__":
    unittest.main()
