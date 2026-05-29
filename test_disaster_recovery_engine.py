import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from disaster_recovery_engine import DisasterRecoveryEngine

class TestDisasterRecoveryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DisasterRecoveryEngine()

    def test_initial_state(self):
        self.assertIsNone(self.engine.active_workflow)
        self.assertEqual(self.engine.workflow_status, "IDLE")
        self.assertEqual(self.engine.restoration_stage, 0)
        self.assertEqual(self.engine.recovery_checkpoints, {})
        self.assertFalse(self.engine.rollback_active)

    def test_start_recovery_workflow(self):
        current_states = {
            "L1_4": "OPEN",
            "L4_5": "OPEN",
            "L5_6": "OPEN"
        }
        success, reason = self.engine.start_recovery_workflow("BLACKSTART_RESTORATION", current_states)
        
        self.assertTrue(success)
        self.assertEqual(self.engine.active_workflow, "BLACKSTART_RESTORATION")
        self.assertEqual(self.engine.workflow_status, "IN_PROGRESS")
        self.assertEqual(self.engine.restoration_stage, 1)
        self.assertEqual(len(self.engine.recovery_checkpoints), 1)
        
        # Test starting unknown workflow
        success2, reason2 = self.engine.start_recovery_workflow("UNKNOWN", current_states)
        self.assertFalse(success2)

    def test_execute_steps_dependency_satisfied(self):
        current_states = {
            "L1_4": "OPEN",
            "L4_5": "OPEN",
            "L5_6": "OPEN"
        }
        self.engine.start_recovery_workflow("BLACKSTART_RESTORATION", current_states)
        
        # Stage 1: targets L1_4, no dependencies (or rather, L1_4 not listed in restoration_dependencies keys)
        cmd = self.engine.execute_next_step(current_states)
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd["command"], "CLOSE")
        self.assertEqual(cmd["target"], "L1_4")
        self.assertEqual(cmd["source"], "SAFETY_GUARD")
        
        # Simulating successful close of L1_4
        current_states["L1_4"] = "CLOSED"
        self.engine.restoration_stage = 2
        
        # Stage 2: targets L4_5, depends on L1_4 (CLOSED)
        cmd2 = self.engine.execute_next_step(current_states)
        self.assertIsNotNone(cmd2)
        self.assertEqual(cmd2["command"], "CLOSE")
        self.assertEqual(cmd2["target"], "L4_5")

    def test_execute_steps_dependency_unsatisfied(self):
        current_states = {
            "L1_4": "OPEN",  # Dep of L4_5 is L1_4 which is OPEN
            "L4_5": "OPEN",
            "L5_6": "OPEN"
        }
        self.engine.start_recovery_workflow("BLACKSTART_RESTORATION", current_states)
        self.engine.restoration_stage = 2  # Skip to step 2 which has dependencies
        
        cmd = self.engine.execute_next_step(current_states)
        self.assertIsNone(cmd)
        self.assertEqual(self.engine.workflow_status, "FAILED")

    def test_handle_step_failure_rollback(self):
        initial_states = {
            "L1_4": "OPEN",
            "L4_5": "CLOSED",
            "L5_6": "OPEN"
        }
        self.engine.start_recovery_workflow("BLACKSTART_RESTORATION", initial_states)
        
        # Change current state, as if we successfully executed some step, but then failed
        current_states = {
            "L1_4": "CLOSED",
            "L4_5": "CLOSED",
            "L5_6": "OPEN"
        }
        
        rollback_cmds = self.engine.handle_step_failure("L4_5", current_states)
        
        self.assertTrue(self.engine.rollback_active)
        self.assertEqual(self.engine.workflow_status, "ROLLING_BACK")
        # Rollback commands should restore L1_4 back to its initial state: OPEN
        self.assertEqual(len(rollback_cmds), 1)
        self.assertEqual(rollback_cmds[0]["command"], "OPEN")
        self.assertEqual(rollback_cmds[0]["target"], "L1_4")
        self.assertEqual(rollback_cmds[0]["source"], "SAFETY_GUARD")

if __name__ == "__main__":
    unittest.main()
