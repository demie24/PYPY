import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from survival_agent import SurvivalAgent

class TestSurvivalAgent(unittest.TestCase):
    def setUp(self):
        self.agent = SurvivalAgent()

    def test_nominal_evaluation(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 1.0}
                },
                "breakers": {
                    "L1_4": "CLOSED",
                    "L2_7": "CLOSED",
                    "L3_9": "CLOSED",
                    "L4_5": "CLOSED",
                    "L4_9": "CLOSED",
                    "L5_6": "CLOSED",
                    "L6_7": "CLOSED",
                    "L7_8": "OPEN",
                    "L8_9": "CLOSED"
                }
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 1.0)
        self.assertEqual(res["proposals"], [])

    def test_compromised_islanding_evaluation(self):
        # Bus_5 voltage drops (hospital at risk)
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 0.82}
                },
                "breakers": {
                    "L1_4": "CLOSED"
                }
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 0.4) # Decayed because hospital is low voltage

    def test_hospital_veto_voting(self):
        # Proposing load shed on hospital (Bus 5) should be vetoed
        vote = self.agent.vote({"command": "SHED_LOAD", "target": "Bus_5"}, {})
        self.assertEqual(vote, -1.0)

        # Proposing load shed on other load buses should be approved
        vote2 = self.agent.vote({"command": "SHED_LOAD", "target": "Bus_6"}, {})
        self.assertGreater(vote2, 0.0)

    def test_hospital_isolation_veto(self):
        # Proposing to open L4_5 when L5_6 is open (would isolate Bus 5) should be vetoed
        proposal = {"command": "OPEN", "target": "L4_5"}
        context = {
            "telemetry": {
                "state": {
                    "breakers": {
                        "L5_6": "OPEN" # already open
                    }
                }
            }
        }
        vote = self.agent.vote(proposal, context)
        self.assertEqual(vote, -1.0)

        # Proposing to open L4_5 when L5_6 is closed should NOT be vetoed
        context2 = {
            "telemetry": {
                "state": {
                    "breakers": {
                        "L5_6": "CLOSED"
                    }
                }
            }
        }
        vote2 = self.agent.vote(proposal, context2)
        self.assertEqual(vote2, 0.0)

if __name__ == "__main__":
    unittest.main()
