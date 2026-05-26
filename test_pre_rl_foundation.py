import os
import sys
import unittest
import numpy as np

# Add core directories to path to ensure test runner can resolve packages
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "self_healing"))
sys.path.append(os.path.join(CURRENT_DIR, "core", "digital_twin"))

# Import pre-RL modules
from restoration_sandbox import RestorationSandbox
from action_rollback import ActionRollbackManager
from state_vector_debugger import StateVectorDebugger
from action_explainer import ActionExplainer
from restoration_timeline import RestorationTimeline
from trusted_action_filter import TrustedActionFilter
from reward_engine import RewardEngine
from safety_constraints import SafetyConstraintEngine
from rl_environment import GridRLEnvironment
from state_encoder import StateEncoder

class TestPreRlFoundation(unittest.TestCase):
    def setUp(self):
        self.sandbox = RestorationSandbox()
        self.rollback = ActionRollbackManager()
        self.debugger = StateVectorDebugger()
        self.explainer = ActionExplainer()
        self.timeline = RestorationTimeline()
        self.filter = TrustedActionFilter()
        self.reward_engine = RewardEngine()
        self.encoder = StateEncoder()
        
    def test_sandbox_isolation_integrity(self):
        """
        Verifies that dry-run actions in RestorationSandbox are isolated 
        and do not permanently affect sandbox state variables.
        """
        # Nominal state: all breakers except L7_8 are CLOSED
        initial_breakers = self.sandbox.breakers.copy()
        
        # Simulating open line dry-run
        res = self.sandbox.dry_run_action("ISOLATE_LINE", "L4_5")
        
        self.assertIn("allowed", res)
        self.assertIn("cascade_risk", res)
        self.assertIn("confidence", res)
        
        # Verify sandbox breakers are unchanged after dry-run completes
        self.assertEqual(self.sandbox.breakers, initial_breakers)

    def test_unsafe_action_rejection(self):
        """
        Verifies that the filter rejects actions violating KCL/KVL, 
        causing islanding, or exceeding line loading thresholds.
        """
        # Create a telemetry state where opening L4_5 would island Bus_5
        telemetry = {
            "state": {
                "buses": {f"Bus_{i}": {"voltage_pu": 1.0, "angle_rad": 0.0} for i in range(1, 10)},
                "lines": {lid: {"P_mw": 10.0, "Q_mvar": 2.0, "current_pu": 0.1} for lid in self.sandbox.breakers.keys()},
                "breakers": {lid: "CLOSED" for lid in self.sandbox.breakers.keys()}
            }
        }
        
        # Open L5_6 first
        telemetry["state"]["breakers"]["L5_6"] = "OPEN"
        # Opening L4_5 now would isolate Bus_5 (Load_5)
        action = {"name": "ISOLATE_LINE", "type": "TRIP", "target": "LINE"}
        
        allowed, reason, metrics = self.filter.filter_action(action, "L4_5", telemetry)
        
        self.assertFalse(allowed)
        self.assertIn("violations", metrics)
        self.assertTrue(len(metrics["violations"]) > 0)
        self.assertTrue(metrics["rollback_recommended"])

    def test_rollback_safety_and_snapshots(self):
        """
        Verifies pushing, popping, and restoring checkpoint snapshots in rollback manager.
        """
        breakers_t0 = {"L1_4": "CLOSED", "L4_5": "CLOSED"}
        trust_t0 = {"bus_trust": {"Bus_1": 1.0}}
        
        # Save checkpoint
        checkpoint = self.rollback.push_checkpoint(breakers_t0, trust_t0)
        self.assertEqual(self.rollback.get_readiness_status()["checkpoints_count"], 1)
        
        # Revert
        restored_breakers, restored_trust = self.rollback.rollback_to_last()
        self.assertEqual(restored_breakers, breakers_t0)
        self.assertEqual(restored_trust, trust_t0)
        self.assertEqual(self.rollback.get_readiness_status()["checkpoints_count"], 0)

    def test_topology_rollback_sequence(self):
        """
        Verifies undo/reversal of multi-step sequence.
        """
        b1 = {"L1_4": "CLOSED"}
        b2 = {"L1_4": "OPEN"}
        
        self.rollback.push_checkpoint(b1)
        self.rollback.push_checkpoint(b2)
        
        # Undo 2 steps
        restored_breakers, _ = self.rollback.undo_sequence(2)
        self.assertEqual(restored_breakers, b1)

    def test_restoration_sequencing(self):
        """
        Verifies sequential rehearsals accumulate topology states correctly inside the sandbox.
        """
        # Sequence of closing L7_8 then closing L4_5 (nominal)
        sequence = [
            ("RECONNECT_LINE", "L7_8"),
            ("NO_ACTION", "SYSTEM")
        ]
        all_safe, step_results = self.sandbox.rehearse_sequence(sequence)
        
        self.assertTrue(all_safe)
        self.assertEqual(len(step_results), 2)
        self.assertEqual(self.sandbox.breakers["L7_8"], "CLOSED")

    def test_action_explainability(self):
        """
        Verifies explanation chain formatting, expected rewards, and reasoning logs.
        """
        state_vec = np.zeros(72)
        state_vec[65] = 0.80 # high cascade risk
        
        explain = self.explainer.explain_action(1, "L4_5", state_vec)
        
        self.assertEqual(explain["action_name"], "ISOLATE_LINE")
        self.assertEqual(explain["target"], "L4_5")
        self.assertTrue(len(explain["reasoning_chain"]) > 0)
        self.assertTrue(explain["expected_cascade_reduction"] > 0)

    def test_telemetry_corruption_and_distrust(self):
        """
        Verifies action rejection when target elements have low telemetry trust.
        """
        action = {"name": "RECONNECT_LINE", "type": "CLOSE", "target": "LINE"}
        telemetry = {"state": {"breakers": {"L1_4": "OPEN"}}}
        
        # Distrusted telemetry target (trust < 50%)
        trust_scores = {"bus_trust": {}, "line_trust": {"L1_4": 30.0}}
        
        allowed, reason, metrics = self.filter.filter_action(
            action, "L1_4", telemetry, trust_scores=trust_scores
        )
        
        self.assertFalse(allowed)
        self.assertIn("Telemetry trust check failed", reason)

    def test_observability_degradation(self):
        """
        Verifies rejection when state observability is degraded.
        """
        action = {"name": "ISOLATE_LINE", "type": "TRIP", "target": "LINE"}
        telemetry = {"state": {"breakers": {"L1_4": "CLOSED"}}}
        
        # Observability confidence too low (confidence = 20%)
        pinn_forecast = {"global_physics_confidence": 0.20, "degraded_observability": True}
        
        allowed, reason, metrics = self.filter.filter_action(
            action, "L1_4", telemetry, pinn_forecast=pinn_forecast
        )
        
        self.assertFalse(allowed)
        self.assertIn("Observability degraded", reason)

    def test_cascading_instability_and_rewards(self):
        """
        Verifies reward balancing and penalties.
        """
        prev_s = np.zeros(72)
        curr_s = np.zeros(72)
        
        # 1. Test stabilization reward
        # Voltages recover from 0.82 to 1.00
        prev_s[0:9] = 0.82
        curr_s[0:9] = 1.00
        reward, details = self.reward_engine.compute_reward(prev_s, curr_s, 0)
        self.assertTrue(details["reward_stability"] > 0.0)
        
        # 2. Test overload amplification penalty
        # Loading increases
        curr_s[18:27] = 1.50
        reward, details = self.reward_engine.compute_reward(prev_s, curr_s, 0)
        self.assertTrue(details["penalty_overload_amplification"] < 0.0)

        # 3. Test false restoration penalty
        # Breaker closed on a low-trust line
        prev_s[36] = 0.0 # open
        curr_s[36] = 1.0 # closed
        curr_s[54] = 0.20 # low trust on line 1
        reward, details = self.reward_engine.compute_reward(prev_s, curr_s, 2)
        self.assertTrue(details["penalty_false_restoration"] < 0.0)

    def test_environment_nan_inf_protection(self):
        """
        Verifies that state encoder outputs have no NaN/Inf values.
        """
        # Telemetry with NaNs
        bad_telemetry = {
            "state": {
                "buses": {"Bus_1": {"voltage_pu": float('nan'), "angle_rad": float('inf')}},
                "lines": {},
                "breakers": {}
            }
        }
        
        vec = self.encoder.encode_state(telemetry=bad_telemetry)
        
        self.assertEqual(len(vec), 72)
        self.assertFalse(np.any(np.isnan(vec)))
        self.assertFalse(np.any(np.isinf(vec)))

if __name__ == "__main__":
    unittest.main()
