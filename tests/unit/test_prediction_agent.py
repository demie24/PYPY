import unittest
import sys
import os

# Setup import paths

from core.self_healing.prediction_agent import PredictionAgent
from core.self_healing.predictive_stability_engine import PredictiveStabilityEngine

class TestPredictionAgent(unittest.TestCase):
    def setUp(self):
        self.predictive_engine = PredictiveStabilityEngine()
        self.agent = PredictionAgent(self.predictive_engine)

    def test_nominal_evaluation(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 1.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 50.0}
                }
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 0.95)
        self.assertEqual(res["collapse_probability"], 0.0)
        self.assertEqual(res["proposals"], [])

    def test_overload_trip_prediction(self):
        # Setup telemetry that triggers overload predictions
        # Frame 1
        tel1 = {
            "state": {
                "buses": {"Bus_5": {"voltage_pu": 1.0}},
                "lines": {"L1_4": {"capacity_pct": 70.0}}
            }
        }
        # Frame 2
        tel2 = {
            "state": {
                "buses": {"Bus_5": {"voltage_pu": 1.0}},
                "lines": {"L1_4": {"capacity_pct": 98.0}} # dc/dt = 28%. Remaining margin = 110 - 98 = 12. Time = 12 / 28 = 0.4s
            }
        }
        self.predictive_engine.update_history(tel1)
        res = self.agent.evaluate(tel2)
        
        # Should propose preemptive isolation on L1_4
        self.assertGreater(len(res["proposals"]), 0)
        self.assertEqual(res["proposals"][0]["command"], "OPEN")
        self.assertEqual(res["proposals"][0]["target"], "L1_4")
        self.assertEqual(res["proposals"][0]["priority"], "CRITICAL") # 0.4s is < 5s

    def test_low_success_veto(self):
        # If success probability is critically low, vote on closing should be vetoed (-1.0)
        vote = self.agent.vote({"command": "CLOSE", "target": "L7_8"}, {"success_probability": 30.0})
        self.assertEqual(vote, -1.0)

        # If success probability is nominal, vote should be 0.0
        vote2 = self.agent.vote({"command": "CLOSE", "target": "L7_8"}, {"success_probability": 85.0})
        self.assertEqual(vote2, 0.0)

if __name__ == "__main__":
    unittest.main()
