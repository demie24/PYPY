import unittest
import sys
import os

# Setup import paths

from core.self_healing.restoration_agent import RestorationAgent
from core.self_healing.recovery_state_machine import RecoveryStateMachine
from core.self_healing.adaptive_recovery_memory import AdaptiveRecoveryMemory

class TestRestorationAgent(unittest.TestCase):
    def setUp(self):
        self.fsm = RecoveryStateMachine()
        self.memory = AdaptiveRecoveryMemory()
        self.agent = RestorationAgent(self.fsm, self.memory)

    def test_nominal_evaluation(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"is_gen": True, "voltage_pu": 1.0},
                    "Bus_5": {"is_load": True, "voltage_pu": 1.0}
                },
                "breakers": {}
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertEqual(res["confidence"], 1.0)
        self.assertEqual(res["fsm_state"], "NORMAL")
        self.assertFalse(res["collapsed"])
        self.assertEqual(res["proposals"], [])

    def test_collapsed_grid_evaluation(self):
        # All generator voltages are 0.0 p.u. (collapsed)
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"is_gen": True, "voltage_pu": 0.0},
                    "Bus_2": {"is_gen": True, "voltage_pu": 0.0},
                    "Bus_3": {"is_gen": True, "voltage_pu": 0.0}
                },
                "breakers": {}
            }
        }
        res = self.agent.evaluate(telemetry)
        self.assertTrue(res["collapsed"])
        self.assertEqual(res["confidence"], 0.5)
        self.assertEqual(len(res["proposals"]), 1)
        self.assertEqual(res["proposals"][0]["command"], "INITIATE_BLACKSTART")
        
        # Test voting
        vote = self.agent.vote({"command": "INITIATE_BLACKSTART", "target": "SYSTEM", "source": "OP"}, {})
        self.assertEqual(vote, 1.0)
        
        # Attempting normal close during collapse should be vetoed
        vote2 = self.agent.vote({"command": "CLOSE", "target": "L7_8", "source": "FLISR"}, {"collapsed": True})
        self.assertEqual(vote2, -1.0)

    def test_lockout_voting(self):
        # Lock out breaker L7_8
        self.fsm.rollback_guard.lockout("L7_8", duration=60.0)
        
        # Vote on closing locked-out breaker should be -1.0
        vote = self.agent.vote({"command": "CLOSE", "target": "L7_8", "source": "FLISR"}, {})
        self.assertEqual(vote, -1.0)

        # Vote on non-locked-out breaker should be 0.0
        vote2 = self.agent.vote({"command": "CLOSE", "target": "L1_4", "source": "FLISR"}, {})
        self.assertEqual(vote2, 0.0)

if __name__ == "__main__":
    unittest.main()
