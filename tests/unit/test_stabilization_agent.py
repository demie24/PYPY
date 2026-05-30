import unittest
import sys
import os

# Setup import paths

from core.self_healing.stabilization_agent import StabilizationAgent

class TestStabilizationAgent(unittest.TestCase):
    def setUp(self):
        self.agent = StabilizationAgent()

    def test_nominal_state(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "frequency_hz": 60.0},
                    "Bus_5": {"voltage_pu": 1.0, "frequency_hz": 60.0}
                },
                "lines": {}
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 1.0)
        self.assertEqual(res["proposals"], [])
        self.assertEqual(res["avg_freq"], 60.0)

    def test_low_frequency_proposals(self):
        # Grid frequency drops to 59.4Hz
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "frequency_hz": 59.4},
                    "Bus_6": {"voltage_pu": 0.98, "frequency_hz": 59.4, "P_mw": 50.0},
                    "Bus_8": {"voltage_pu": 0.99, "frequency_hz": 59.4, "P_mw": 40.0}
                },
                "lines": {}
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertLess(res["confidence"], 1.0)
        self.assertEqual(res["avg_freq"], 59.4)
        # Should propose SHED_LOAD on Bus_6 and Bus_8
        self.assertEqual(len(res["proposals"]), 2)
        targets = [p["target"] for p in res["proposals"]]
        self.assertIn("Bus_6", targets)
        self.assertIn("Bus_8", targets)

        # Test voting: should endorse SHED_LOAD because frequency is low
        vote = self.agent.vote({"command": "SHED_LOAD", "target": "Bus_6"}, {"avg_freq": 59.1})
        self.assertEqual(vote, 1.0)

    def test_overload_veto(self):
        # Try to close a line that is overloaded
        proposal = {"command": "CLOSE", "target": "L1_4"}
        context = {
            "telemetry": {
                "state": {
                    "lines": {
                        "L1_4": {"capacity_pct": 115.0}
                    }
                }
            }
        }
        vote = self.agent.vote(proposal, context)
        self.assertEqual(vote, -1.0) # Veto

if __name__ == "__main__":
    unittest.main()
