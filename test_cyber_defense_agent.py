import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from cyber_defense_agent import CyberDefenseAgent

class TestCyberDefenseAgent(unittest.TestCase):
    def setUp(self):
        self.agent = CyberDefenseAgent()

    def test_nominal_state(self):
        telemetry = {
            "attack_status": {
                "active_attack": None,
                "compromised_nodes": {}
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 1.0)
        self.assertEqual(res["proposals"], [])
        
        # Test voting on nominal proposal
        vote = self.agent.vote({"command": "CLOSE", "target": "L7_8", "source": "FLISR"}, {})
        self.assertEqual(vote, 0.0)

    def test_compromised_state(self):
        telemetry = {
            "attack_status": {
                "active_attack": "FDIA",
                "compromised_nodes": {"Bus_7": {"attack_type": "FDIA"}}
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 0.7)
        self.assertEqual(len(res["proposals"]), 2) # REJECT_TELEMETRY + LOCKDOWN_BREAKER
        targets = [p["target"] for p in res["proposals"]]
        self.assertIn("Bus_7", targets)

        # Test voting on compromised line close
        vote = self.agent.vote({"command": "CLOSE", "target": "L2_7", "source": "FLISR"}, {})
        self.assertEqual(vote, -1.0) # Veto

        # Test voting on compromised bus close
        vote2 = self.agent.vote({"command": "RECONNECT_LINE", "target": "Bus_7", "source": "FLISR"}, {})
        self.assertEqual(vote2, -1.0) # Veto

    def test_unauthenticated_source_during_attack(self):
        telemetry = {
            "attack_status": {
                "active_attack": "coordinated_cascade",
                "compromised_nodes": {}
            }
        }
        self.agent.evaluate(telemetry)
        
        # Vote on action from unauthenticated source should be -1.0 (veto)
        vote = self.agent.vote({"command": "CLOSE", "target": "L7_8", "source": "UNTRUSTED_OP"}, {})
        self.assertEqual(vote, -1.0)

        # Vote on action from authenticated source should be 0.0 (neutral)
        vote2 = self.agent.vote({"command": "CLOSE", "target": "L7_8", "source": "AGENT_CONSENSUS"}, {})
        self.assertEqual(vote2, 0.0)

if __name__ == "__main__":
    unittest.main()
