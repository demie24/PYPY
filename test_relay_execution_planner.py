import unittest
import sys
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from relay_execution_planner import RelayExecutionPlanner

class TestRelayExecutionPlanner(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.planner = RelayExecutionPlanner(self.mgr)
        
    def test_switching_plan_creation_and_interlocks(self):
        # Good plan
        steps = [
            {"command": "OPEN", "target": "L4_5", "delay_ms": 100},
            {"command": "CLOSE", "target": "L7_8", "delay_ms": 100}
        ]
        success, msg = self.planner.create_switching_plan("plan_01", steps)
        self.assertTrue(success)
        self.assertIn("plan_01", self.planner.active_plans)
        
        # Bad plan: Opening all generator transformers L1_4, L2_7, L3_9 (isolates generators)
        bad_steps = [
            {"command": "OPEN", "target": "L1_4", "delay_ms": 100},
            {"command": "OPEN", "target": "L2_7", "delay_ms": 100},
            {"command": "OPEN", "target": "L3_9", "delay_ms": 100}
        ]
        success2, msg2 = self.planner.create_switching_plan("plan_02", bad_steps)
        self.assertFalse(success2)
        self.assertIn("isolate", msg2)

    def test_plan_execution_ticking(self):
        steps = [
            {"command": "OPEN", "target": "L4_5", "delay_ms": 100},
            {"command": "CLOSE", "target": "L7_8", "delay_ms": 100}
        ]
        self.planner.create_switching_plan("plan_03", steps)
        
        # First tick dispatches step 0
        dispatched = self.planner.tick_plans(time.time())
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0][0], "plan_03")
        self.assertEqual(dispatched[0][1], 0) # step 0
        self.assertEqual(dispatched[0][2]["target"], "L4_5")
        
        # Update placeholder tx_id
        self.planner.active_plans["plan_03"]["active_tx_id"] = "tx_01"
        
        # Advance step 0 success
        self.planner.mark_step_result("plan_03", 0, success=True, tx_id="tx_01")
        self.assertEqual(self.planner.active_plans["plan_03"]["current_step_idx"], 1)

    def test_rollback_sequence_triggering(self):
        steps = [
            {"command": "OPEN", "target": "L4_5", "delay_ms": 100},
            {"command": "CLOSE", "target": "L7_8", "delay_ms": 100}
        ]
        self.planner.create_switching_plan("plan_04", steps)
        
        # Tick and execute step 0
        self.planner.tick_plans(time.time())
        self.planner.active_plans["plan_04"]["active_tx_id"] = "tx_01"
        self.planner.mark_step_result("plan_04", 0, success=True, tx_id="tx_01")
        
        # Tick and fail step 1
        self.planner.tick_plans(time.time())
        self.planner.active_plans["plan_04"]["active_tx_id"] = "tx_02"
        self.planner.mark_step_result("plan_04", 1, success=False, tx_id="tx_02", reason="Coil failed to engage")
        
        # Status should transition to ROLLBACK
        plan = self.planner.active_plans["plan_04"]
        self.assertEqual(plan["status"], "ROLLBACK")
        self.assertEqual(plan["error"], "Coil failed to engage")
        
        # Rollback steps should be the opposite of step 0 (CLOSE L4_5)
        self.assertEqual(len(plan["rollback_steps"]), 1)
        self.assertEqual(plan["rollback_steps"][0]["command"], "CLOSE")
        self.assertEqual(plan["rollback_steps"][0]["target"], "L4_5")

if __name__ == "__main__":
    unittest.main()
