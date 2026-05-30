import os
import sys
import unittest
import json
import time
import numpy as np

# Set pythonpath dynamically

from core.self_healing.rl.rl_metrics import calculate_grid_survivability, calculate_blackout_risk, calculate_recovery_efficiency, compile_comprehensive_metrics
from core.self_healing.reward_engine import RewardEngine
from core.self_healing.rl_environment import GridRLEnvironment
from core.orchestrator.ai_orchestrator import AIOrchestrator

class TestAIOrchestrationMaturity(unittest.TestCase):
    def setUp(self):
        self.reward_engine = RewardEngine()
        self.env = GridRLEnvironment(is_live_mode=False)
        self.orchestrator = AIOrchestrator()
        
        # Simple mock telemetry
        self.mock_telemetry = {
            "timestamp": int(time.time() * 1000),
            "state": {
                "breakers": {
                    "L1_4": "CLOSED", "L2_7": "CLOSED", "L3_9": "CLOSED",
                    "L4_5": "CLOSED", "L4_9": "CLOSED", "L5_6": "CLOSED",
                    "L6_7": "CLOSED", "L7_8": "OPEN", "L8_9": "CLOSED"
                },
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0}, "Bus_2": {"voltage_pu": 1.0}, "Bus_3": {"voltage_pu": 1.0},
                    "Bus_4": {"voltage_pu": 1.0}, "Bus_5": {"voltage_pu": 1.0}, "Bus_6": {"voltage_pu": 1.0},
                    "Bus_7": {"voltage_pu": 1.0}, "Bus_8": {"voltage_pu": 1.0}, "Bus_9": {"voltage_pu": 1.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 50.0}, "L2_7": {"capacity_pct": 50.0}, "L3_9": {"capacity_pct": 50.0},
                    "L4_5": {"capacity_pct": 50.0}, "L4_9": {"capacity_pct": 50.0}, "L5_6": {"capacity_pct": 50.0},
                    "L6_7": {"capacity_pct": 50.0}, "L7_8": {"capacity_pct": 0.0}, "L8_9": {"capacity_pct": 50.0}
                }
            }
        }

    def test_rl_metrics_compilation(self):
        """Verify that rl_metrics compiles all new maturity metrics properly."""
        metrics = compile_comprehensive_metrics(
            telemetry=self.mock_telemetry,
            actual_steps=4,
            step_count=5,
            rollbacks=1,
            switch_count=3,
            start_time=time.time() - 10.0,
            compromised_nodes=["Bus_5"],
            isolated_nodes=["Bus_5"],
            ppo_probs=np.array([0.1, 0.8, 0.05, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            action_id=1,
            cascade_prob=0.15
        )
        
        self.assertIn("restoration_latency_steps", metrics)
        self.assertIn("topology_survivability_score", metrics)
        self.assertIn("blackout_risk_pct", metrics)
        self.assertIn("containment_efficiency_pct", metrics)
        self.assertIn("restoration_efficiency_pct", metrics)
        self.assertIn("policy_confidence_pct", metrics)
        self.assertIn("relay_switch_count", metrics)
        self.assertIn("rollback_frequency", metrics)
        self.assertIn("recovery_duration_seconds", metrics)
        
        self.assertEqual(metrics["restoration_latency_steps"], 5)
        self.assertEqual(metrics["relay_switch_count"], 3)
        self.assertEqual(metrics["rollback_frequency"], 1)
        self.assertEqual(metrics["containment_efficiency_pct"], 100.0)
        self.assertEqual(metrics["policy_confidence_pct"], 80.0)

    def test_reward_engine_tuning(self):
        """Verify new penalties in the reward engine: unsafe switching, repeated failure, and latency."""
        state_dim = 72
        prev_state = np.zeros(state_dim)
        curr_state = np.zeros(state_dim)
        
        # Set voltages to nominal
        prev_state[0:9] = 1.0
        curr_state[0:9] = 1.0
        
        # Set breakers (simulate switch)
        prev_state[36:45] = 1.0
        curr_state[36:45] = 1.0
        curr_state[36] = 0.0 # line L1_4 breaker opened
        
        # 1. Check unsafe switching penalty (-5.0 instead of -3.0)
        _, details = self.reward_engine.compute_reward(
            prev_state, curr_state, action_id=1, rollback_occurred=False, repeated_failed_action=False, step_count=1
        )
        self.assertEqual(details["penalty_unsafe_breaker_switching"], -5.0)
        
        # 2. Check repeated failed action penalty (-15.0)
        _, details_fail = self.reward_engine.compute_reward(
            prev_state, curr_state, action_id=1, rollback_occurred=False, repeated_failed_action=True, step_count=1
        )
        self.assertEqual(details_fail["penalty_repeated_failure"], -15.0)
        
        # 3. Check latency penalty (-0.5 * max(0, step_count - 5))
        _, details_latency = self.reward_engine.compute_reward(
            prev_state, curr_state, action_id=1, rollback_occurred=False, repeated_failed_action=False, step_count=10
        )
        # 10 steps should incur -0.5 * (10-5) = -2.5 latency penalty
        self.assertEqual(details_latency["penalty_latency"], -2.5)

    def test_env_adaptive_ppo_blocking(self):
        """Verify that GridRLEnvironment blocks repeated failed actions dynamically."""
        self.env.reset()
        
        # Simulate a failed action by registering it as failed
        action_name = "RECONNECT_LINE"
        target = "L1_4"
        self.env.episode_failed_actions.add((action_name, target))
        
        # Action ID 2 corresponds to RECONNECT_LINE
        action_id = 2 
        
        obs, reward, terminated, truncated, info = self.env.step(action_id, target)
        
        # Should be blocked, and return action_allowed=False
        self.assertFalse(info["action_allowed"])
        self.assertIn("repeated failed action", info["rejection_reason"])
        
        # Verify repeated failure penalty is computed
        self.assertEqual(info["reward_details"]["penalty_repeated_failure"], -15.0)

    def test_orchestrator_proposed_interception(self):
        """Verify that AIOrchestrator evaluates and coordinates proposed actions correctly."""
        self.orchestrator.reset()
        
        # Feed nominal telemetry
        self.orchestrator.update_state("grid/telemetry", self.mock_telemetry)
        
        # Proposal 1: Normal recovery (voltage stability is high)
        approved, reason = self.orchestrator.evaluate_proposed_command("CLOSED", "L1_4", "FLISR")
        self.assertTrue(approved)
        self.assertIn("Passed all", reason)
        
        # Proposal 2: Unstable recovery (simulate low stability)
        low_stab_telemetry = json.loads(json.dumps(self.mock_telemetry))
        # Drop voltages to drop stability
        for b in low_stab_telemetry["state"]["buses"].values():
            b["voltage_pu"] = 0.80
        self.orchestrator.update_state("grid/telemetry", low_stab_telemetry)
        
        approved, reason = self.orchestrator.evaluate_proposed_command("CLOSED", "L1_4", "FLISR")
        # Should block since stability is low
        self.assertFalse(approved)
        self.assertIn("Blocked restoration under low stability", reason)

    def test_orchestrator_guard_delay(self):
        """Verify that AIOrchestrator enforces the 3-second guard delay between breaker commands."""
        self.orchestrator.reset()
        self.orchestrator.update_state("grid/telemetry", self.mock_telemetry)
        
        # First breaker command (approved and updates self.last_breaker_operation_time)
        approved, _ = self.orchestrator.evaluate_proposed_command("CLOSED", "L1_4", "FLISR")
        self.assertTrue(approved)
        
        # Second breaker command immediately after (should be rejected by guard delay)
        approved_immediate, reason = self.orchestrator.evaluate_proposed_command("CLOSED", "L2_7", "FLISR")
        self.assertFalse(approved_immediate)
        self.assertIn("3-second guard delay", reason)

    def test_orchestrator_escalation_modes(self):
        """Verify the logic for active escalation modes and dominant decision source updates."""
        self.orchestrator.reset()
        
        # Setup telemetry
        self.orchestrator.update_state("grid/telemetry", self.mock_telemetry)
        
        # 1. Local Attack mode
        defense_payload = {"escalation_level": "LOCAL_CONTAINMENT", "breaker_lockdown_targets": ["L1_4"]}
        self.orchestrator.update_state("grid/defense", defense_payload)
        
        class MockClient:
            def __init__(self):
                self.published = []
            def publish(self, topic, payload):
                self.published.append((topic, json.loads(payload)))
                
        client = MockClient()
        self.orchestrator.run_cycle(client)
        
        # Find published orchestrator data
        orch_data = next(p[1] for p in client.published if p[0] == "grid/ai_orchestrator")
        self.assertEqual(orch_data["escalation_mode"], "LOCAL_ATTACK")
        self.assertEqual(orch_data["coordinated_recovery_state"], "CONTAINMENT_ENGAGED")
        
        # 2. Coordinated Attack mode
        client.published.clear()
        coord_defense = {"escalation_level": "EMERGENCY_CONTAINMENT", "breaker_lockdown_targets": ["L1_4", "L2_7"]}
        self.orchestrator.update_state("grid/defense", coord_defense)
        self.orchestrator.run_cycle(client)
        
        orch_data = next(p[1] for p in client.published if p[0] == "grid/ai_orchestrator")
        self.assertEqual(orch_data["escalation_mode"], "COORDINATED_ATTACK")
        self.assertEqual(orch_data["dominant_decision_source"], "DEFENSE")

if __name__ == "__main__":
    unittest.main()
