import unittest
import sys
import os

# Setup import paths

from core.self_healing.orchestrator_agent import OrchestratorAgent

class MockClient:
    def __init__(self):
        self.published = []
    def publish(self, topic, payload):
        self.published.append((topic, json.loads(payload) if isinstance(payload, str) else payload))

import json

class TestOrchestratorAgent(unittest.TestCase):
    def setUp(self):
        self.agent = OrchestratorAgent()
        self.client = MockClient()

    def test_dynamic_weights_adjustment(self):
        # Nominal weights
        self.agent.update_dynamic_weights({})
        self.assertEqual(self.agent.agent_weights["CyberDefenseAgent"], 1.0)
        self.assertEqual(self.agent.agent_weights["StabilizationAgent"], 1.0)

        # Active attack weight scaling
        self.agent.update_dynamic_weights({"active_attack": "FDIA"})
        self.assertEqual(self.agent.agent_weights["CyberDefenseAgent"], 2.5)

        # Low frequency weight scaling
        self.agent.update_dynamic_weights({"avg_freq": 59.3})
        self.assertEqual(self.agent.agent_weights["CyberDefenseAgent"], 1.0)
        self.assertEqual(self.agent.agent_weights["StabilizationAgent"], 2.0)
        self.assertEqual(self.agent.agent_weights["SurvivalAgent"], 2.0)

    def test_trust_adaptation(self):
        # Starting trust is 1.0
        self.assertEqual(self.agent.agent_trust["RestorationAgent"], 1.0)
        
        # Penalize trust on rollback
        rolled_back = [{"source": "FLISR", "command": "CLOSE", "target": "L7_8"}]
        self.agent.adapt_trust(rolled_back_sequence=rolled_back)
        # RestorationAgent trust should decrease
        self.assertLess(self.agent.agent_trust["RestorationAgent"], 1.0)
        
        # Penalize trust on safety violation
        violation = {"source": "AUTONOMOUS_BALANCER", "command": "SHED_LOAD", "target": "Bus_5"}
        self.agent.adapt_trust(safety_violation_cmd=violation)
        self.assertLess(self.agent.agent_trust["StabilizationAgent"], 1.0)

        # Reward on success
        self.agent.adapt_trust(success_sequence=[])
        self.assertGreater(self.agent.agent_trust["RestorationAgent"], 0.7)

    def test_evaluate_and_publish(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"is_gen": True, "voltage_pu": 1.0, "frequency_hz": 60.0},
                    "Bus_5": {"is_load": True, "voltage_pu": 1.0, "frequency_hz": 60.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 50.0}
                },
                "breakers": {}
            },
            "attack_status": {
                "active_attack": None,
                "compromised_nodes": {}
            }
        }
        approved = self.agent.evaluate_and_publish(telemetry, self.client)
        
        # Verify MQTT broadcasts
        topics = [t[0] for t in self.client.published]
        self.assertIn("grid/l6_agents", topics)
        self.assertIn("grid/l6_agent_consensus", topics)
        self.assertIn("grid/l6_agent_conflicts", topics)
        self.assertIn("grid/l6_distributed_state", topics)
        self.assertIn("grid/l6_agent_confidence", topics)

if __name__ == "__main__":
    unittest.main()
