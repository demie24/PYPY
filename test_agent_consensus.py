import unittest
import sys
import os
import json

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from orchestrator_agent import OrchestratorAgent

class MockClient:
    def __init__(self):
        self.published = []
    def publish(self, topic, payload):
        self.published.append((topic, json.loads(payload) if isinstance(payload, str) else payload))

class TestAgentConsensus(unittest.TestCase):
    def setUp(self):
        self.orchestrator = OrchestratorAgent()
        self.client = MockClient()

    def test_cyber_attack_consensus_flow(self):
        # 1. Simulate active attack on Bus 7
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"is_gen": True, "voltage_pu": 1.0, "frequency_hz": 60.0},
                    "Bus_7": {"is_load": True, "voltage_pu": 1.0, "frequency_hz": 60.0}
                },
                "lines": {
                    "L2_7": {"capacity_pct": 50.0}
                },
                "breakers": {
                    "L2_7": "CLOSED"
                }
            },
            "attack_status": {
                "active_attack": "stealthy_fdia",
                "compromised_nodes": {"Bus_7": {"attack_type": "FDIA"}}
            }
        }
        
        # In this state, CyberDefenseAgent should propose LOCKDOWN_BREAKER for Bus_7.
        # If someone proposes to CLOSE L2_7, CyberDefenseAgent should VETO it (-1.0).
        approved = self.orchestrator.evaluate_and_publish(telemetry, self.client)
        
        # Verify CyberDefenseAgent weight is scaled to 2.5
        self.assertEqual(self.orchestrator.agent_weights["CyberDefenseAgent"], 2.5)
        
        # Verify proposals generated
        proposals = [t[1]["proposals"] for t in self.client.published if t[0] == "grid/l6_agents"][0]
        commands = [p["command"] for p in proposals]
        self.assertIn("LOCKDOWN_BREAKER", commands)
        self.assertIn("REJECT_TELEMETRY", commands)
        
        # Simulate a proposed restoration CLOSE command on compromised line L2_7
        # CyberDefenseAgent should cast a veto (-1.0), so overall consensus fails (approved is False)
        proposal = {"command": "CLOSE", "target": "L2_7", "source": "FLISR"}
        res = self.orchestrator.vote_on_proposal(proposal, {
            "telemetry": telemetry,
            "active_attack": "stealthy_fdia",
            "collapsed": False
        })
        self.assertTrue(res["has_veto"])
        self.assertIn("CyberDefenseAgent", res["vetoed_by"])
        self.assertFalse(res["approved"])

    def test_frequency_collapse_consensus_flow(self):
        # 2. Simulate frequency collapse (59.2Hz) and Bus 6/8 load shedding proposals
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"is_gen": True, "voltage_pu": 1.0, "frequency_hz": 59.2},
                    "Bus_5": {"is_load": True, "voltage_pu": 1.0, "frequency_hz": 59.2, "P_mw": 125.0},
                    "Bus_6": {"is_load": True, "voltage_pu": 1.0, "frequency_hz": 59.2, "P_mw": 90.0},
                    "Bus_8": {"is_load": True, "voltage_pu": 1.0, "frequency_hz": 59.2, "P_mw": 100.0}
                },
                "lines": {},
                "breakers": {}
            },
            "attack_status": {
                "active_attack": None,
                "compromised_nodes": {}
            }
        }
        
        # StabilizationAgent should propose shedding load on Bus 6 and Bus 8
        approved = self.orchestrator.evaluate_and_publish(telemetry, self.client)
        approved_commands = [(a["command"], a["target"]) for a in approved]
        
        # Both load shed proposals on Bus 6 and Bus 8 should be approved (no vetoes)
        self.assertIn(("SHED_LOAD", "Bus_6"), approved_commands)
        self.assertIn(("SHED_LOAD", "Bus_8"), approved_commands)
        
        # Attempt to shed critical Bus 5 (hospital) should be VETOED by SurvivalAgent
        proposal_bus5 = {"command": "SHED_LOAD", "target": "Bus_5", "source": "AUTONOMOUS_BALANCER"}
        res_bus5 = self.orchestrator.vote_on_proposal(proposal_bus5, {
            "telemetry": telemetry,
            "avg_freq": 59.2
        })
        self.assertTrue(res_bus5["has_veto"])
        self.assertIn("SurvivalAgent", res_bus5["vetoed_by"])
        self.assertFalse(res_bus5["approved"])

    def test_overloaded_line_veto_flow(self):
        # 3. Simulate closing an overloaded line (capacity > 110%)
        telemetry = {
            "state": {
                "buses": {},
                "lines": {
                    "L1_4": {"capacity_pct": 115.0}
                },
                "breakers": {}
            },
            "attack_status": {
                "active_attack": None,
                "compromised_nodes": {}
            }
        }
        # Proposal to close overloaded line L1_4
        proposal = {"command": "CLOSE", "target": "L1_4", "source": "FLISR"}
        res = self.orchestrator.vote_on_proposal(proposal, {
            "telemetry": telemetry,
            "avg_freq": 60.0
        })
        # StabilizationAgent should veto
        self.assertTrue(res["has_veto"])
        self.assertIn("StabilizationAgent", res["vetoed_by"])
        self.assertFalse(res["approved"])

if __name__ == "__main__":
    unittest.main()
