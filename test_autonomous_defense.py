import unittest
import sys
import os
import json
import time
import numpy as np
from unittest.mock import MagicMock

# Add core directories to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "cyber_defense")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from defense_escalation import DefenseEscalator
from campaign_response_engine import CampaignResponseEngine
from adaptive_defense_engine import AdaptiveDefenseEngine
from autonomous_defense_coordinator import AutonomousDefenseCoordinator
from containment_engine import ContainmentEngine
from defense_memory import DefenseMemory
from campaign_timeline import CampaignTimeline
from rl_environment import GridRLEnvironment
from reward_engine import RewardEngine

class TestAutonomousDefense(unittest.TestCase):
    def setUp(self):
        self.escalator = DefenseEscalator()
        self.campaign = CampaignResponseEngine()
        self.adaptive = AdaptiveDefenseEngine()
        self.coordinator = AutonomousDefenseCoordinator()
        self.containment = ContainmentEngine()
        self.memory = DefenseMemory()
        self.timeline = CampaignTimeline()
        self.reward_engine = RewardEngine()

    def test_defense_escalation_and_hysteresis(self):
        """Verifies escalation transitions and de-escalation hysteresis checks."""
        # 1. Start at baseline
        status = self.escalator.evaluate_escalation(
            threat_score=10,
            campaign_severity=0,
            physics_anomaly=5.0,
            pinn_confidence=0.95,
            islanding_active=False,
            stability_score=95.0
        )
        self.assertEqual(status["escalation_level"], "ADVISORY")

        # 2. Escalate instantly on severe threat
        status = self.escalator.evaluate_escalation(
            threat_score=85,
            campaign_severity=80,
            physics_anomaly=75.0,
            pinn_confidence=0.30,
            islanding_active=False,
            stability_score=25.0
        )
        self.assertEqual(status["escalation_level"], "GRID_PRESERVATION")

        # 3. Try to de-escalate immediately: should stay locked at GRID_PRESERVATION due to hysteresis
        status = self.escalator.evaluate_escalation(
            threat_score=10,
            campaign_severity=0,
            physics_anomaly=5.0,
            pinn_confidence=0.95,
            islanding_active=False,
            stability_score=95.0
        )
        self.assertEqual(status["escalation_level"], "GRID_PRESERVATION")
        self.assertEqual(status["de_escalation_progress_pct"], 10)  # 1/10 ticks

        # 4. Tick 9 more times to complete hysteresis cooldown
        for _ in range(8):
            self.escalator.evaluate_escalation(
                threat_score=10, campaign_severity=0, physics_anomaly=5.0,
                pinn_confidence=0.95, islanding_active=False, stability_score=95.0
            )
        
        # 10th tick -> de-escalates to ADVISORY
        status = self.escalator.evaluate_escalation(
            threat_score=10, campaign_severity=0, physics_anomaly=5.0,
            pinn_confidence=0.95, islanding_active=False, stability_score=95.0
        )
        self.assertEqual(status["escalation_level"], "ADVISORY")

    def test_campaign_correlation_and_stages(self):
        """Verifies parsing and stages of multi-stage cyber campaigns."""
        # 1. Normal state: no alerts
        report = self.campaign.analyze_campaigns(alerts=[], events=[])
        self.assertFalse(report["campaign_detected"])
        self.assertEqual(report["campaign_severity_score"], 0)

        # 2. Initial intrusion alert
        alert1 = {"type": "FDIA", "target": "Bus_5", "severity": "WARNING", "timestamp": int(time.time() * 1000)}
        report = self.campaign.analyze_campaigns(alerts=[alert1], events=[])
        self.assertTrue(report["campaign_detected"])
        self.assertEqual(report["active_campaigns"][0]["stage"], "INITIAL_COMPROMISE")

        # 3. Multiple alerts -> COORDINATED_STRIKE
        alert2 = {"type": "DOS", "target": "Bus_6", "severity": "HIGH", "timestamp": int(time.time() * 1000)}
        report = self.campaign.analyze_campaigns(alerts=[alert1, alert2], events=[])
        self.assertEqual(report["active_campaigns"][0]["stage"], "COORDINATED_STRIKE")

    def test_adaptive_defense_thresholds(self):
        """Tests that adaptive engine updates thresholds dynamically on persistence."""
        # Baseline
        report = self.adaptive.update_and_adapt(telemetry={}, alerts=[], current_trust_scores={})
        self.assertEqual(report["adaptive_trust_threshold"], 50.0)

        # Attack alerts triggering persistence
        alerts = [{"type": "FDIA", "target": "Bus_5"} for _ in range(12)]
        report = self.adaptive.update_and_adapt(telemetry={}, alerts=alerts, current_trust_scores={})
        
        # Persistent alerts shift trust thresholds and decay speeds
        self.assertEqual(report["adaptive_trust_threshold"], 70.0)
        self.assertEqual(report["trust_penalty_multiplier"], 2.0)
        self.assertEqual(report["filtering_smoothing_alpha"], 0.15)

    def test_coordinated_containment(self):
        """Tests coordinate containment logic and breaker lockdown dispatches."""
        telemetry = {
            "state": {
                "lines": {"L4_5": {"capacity_pct": 110.0}},
                "breakers": {"L4_5": "CLOSED"}
            },
            "attack_status": {
                "active_attack": True,
                "compromised_nodes": {"Bus_5": {}}
            }
        }
        trust_scores = {
            "bus_trust": {"Bus_4": 25.0},
            "line_trust": {"L4_5": 90.0}
        }
        threat_data = {"cascade_probability": 0.85}
        pinn_forecast = {"degraded_observability": False}
        physics_val = {"physics_anomaly_score": 45.0}

        # Coordinate containment
        coordinated = self.coordinator.coordinate(
            telemetry=telemetry,
            threat_data=threat_data,
            trust_scores=trust_scores,
            pinn_forecast=pinn_forecast,
            physics_val=physics_val,
            escalation_level="EMERGENCY_CONTAINMENT"
        )

        self.assertTrue(coordinated["restoration_lockdown_active"])
        # Should lock down lines connected to compromised Bus_5: L4_5 and L5_6
        self.assertIn("L4_5", coordinated["breaker_lockdown_targets"])
        self.assertIn("L5_6", coordinated["breaker_lockdown_targets"])

        # Containment dispatch validation
        mock_client = MagicMock()
        dispatched = self.containment.dispatch_containment(coordinated, mock_client)
        
        # Verify MQTT publish dispatches control commands
        self.assertTrue(mock_client.publish.called)
        self.assertIn("L4_5", self.containment.locked_breakers)

    def test_rl_gating_and_defense_aware_rewards(self):
        """Asserts RL restoration suppression and defense-aware penalty bounds."""
        env = GridRLEnvironment(is_live_mode=True)
        
        # Simulate active containment: restoration is locked, breaker L4_5 is under lockdown
        env.latest_defense = {
            "escalation_level": "EMERGENCY_CONTAINMENT",
            "restoration_lockdown_active": True,
            "breaker_lockdown_targets": ["L4_5"],
            "recommended_defense_actions": [{"action": "ISOLATE_LINE", "target": "L4_5"}]
        }

        # Step sandbox environment with a reconnect action (action ID 2 = RECONNECT_LINE)
        env.sandbox_active = True
        env.sandbox_breakers["L4_5"] = "OPEN"
        obs, reward, terminated, truncated, info = env.step(action_id=2, target="L4_5")

        # Action must be blocked by defense containment
        self.assertFalse(info["action_allowed"])
        self.assertIn("blocked by active cyber defense containment", info["rejection_reason"])

        # Check reward engine signals
        prev_obs = np.ones(72, dtype=np.float32)
        curr_obs = np.ones(72, dtype=np.float32)
        # Action ID 2 = RECONNECT_LINE (Restoration)
        rew_val, rew_details = self.reward_engine.compute_reward(
            prev_obs, curr_obs, action_id=2, defense_status=env.latest_defense
        )
        # Verify heavy penalty is applied
        self.assertEqual(rew_details["penalty_defense_violation"], -10.0)

        # Action ID 1 = ISOLATE_LINE (Containment, aligned with recommendation)
        rew_val, rew_details = self.reward_engine.compute_reward(
            prev_obs, curr_obs, action_id=1, defense_status=env.latest_defense
        )
        # Verify positive alignment reward is applied
        self.assertEqual(rew_details["reward_defense_alignment"], 20.0)

    def test_nan_inf_protection(self):
        """Verifies state encoder and reward engine are protected against NaNs and Infs."""
        # 1. State vector nan protection
        env = GridRLEnvironment(is_live_mode=True)
        bad_telemetry = {
            "state": {
                "buses": {"Bus_1": {"voltage_pu": float("nan"), "angle_rad": float("inf")}},
                "lines": {},
                "breakers": {}
            }
        }
        vec = env.encoder.encode_state(telemetry=bad_telemetry)
        self.assertTrue(np.all(np.isfinite(vec)))

        # 2. Reward engine nan protection
        bad_prev = np.array([float("nan")] * 72, dtype=np.float32)
        bad_curr = np.array([float("inf")] * 72, dtype=np.float32)
        rew, details = self.reward_engine.compute_reward(bad_prev, bad_curr, action_id=0)
        self.assertTrue(np.isfinite(rew))
        self.assertEqual(rew, -2.0)

if __name__ == "__main__":
    unittest.main()
