import unittest
import time
import json
import random
from unittest.mock import MagicMock, patch

from core.digital_twin.main import SmartGridDigitalTwin
from core.physics_validation.validation_engine import PhysicsValidationEngine

class TestCyberattackRealism(unittest.TestCase):
    def setUp(self):
        self.twin = SmartGridDigitalTwin()
        # Mock publisher to avoid actual MQTT network calls
        self.twin.publisher = MagicMock()

    @patch("time.time")
    def test_breaker_cooldown(self, mock_time):
        """Verifies breaker cooldown enforcement where commands within 5s are blocked."""
        mock_time.return_value = 100.0
        
        # Clear cooldowns/states
        self.twin.breaker_cooldowns.clear()
        self.twin.breakers["L4_5"] = "CLOSED"
        
        # First command: OPEN at t=100.0 (Allowed)
        self.twin.handle_control_cmd("L4_5", "OPEN", {"source": "OPERATOR"})
        self.assertEqual(self.twin.breakers["L4_5"], "OPEN")
        self.assertEqual(self.twin.breaker_cooldowns["L4_5"], 100.0)
        
        # Second command: CLOSE at t=102.0 (only 2s later) -> should be blocked by cooldown
        mock_time.return_value = 102.0
        self.twin.handle_control_cmd("L4_5", "CLOSE", {"source": "OPERATOR"})
        # Should remain OPEN
        self.assertEqual(self.twin.breakers["L4_5"], "OPEN")
        self.twin.publisher.publish_event.assert_called_with(
            source="SCADA_GATEWAY",
            event_desc="Control command BLOCKED: Breaker 'L4_5' cooldown active.",
            severity="WARNING"
        )
        
        # Third command: CLOSE at t=105.1 (5.1s since last successful op) -> should be allowed
        mock_time.return_value = 105.1
        self.twin.handle_control_cmd("L4_5", "CLOSE", {"source": "OPERATOR"})
        self.assertEqual(self.twin.breakers["L4_5"], "CLOSED")
        self.assertEqual(self.twin.breaker_cooldowns["L4_5"], 105.1)

    @patch("time.time")
    def test_attack_rate_limiting(self, mock_time):
        """Asserts that starting >2 attacks within 10 seconds is rate-limited and blocked."""
        mock_time.return_value = 200.0
        self.twin.active_compromises.clear()
        self.twin.attack_rate_limit_bucket.clear()
        
        # 1. First attack: allowed
        payload1 = {"action": "START", "type": "FDIA", "config": {"target": "Bus_5", "bias": 0.1}}
        self.twin.handle_attack_cmd(payload1)
        self.assertIn("Bus_5", self.twin.active_compromises)
        
        # 2. Second attack at t=202.0: allowed
        mock_time.return_value = 202.0
        payload2 = {"action": "START", "type": "DOS", "config": {"target": "Bus_6"}}
        self.twin.handle_attack_cmd(payload2)
        self.assertIn("Bus_6", self.twin.active_compromises)
        
        # 3. Third attack at t=205.0 -> should be blocked by rate limiting
        mock_time.return_value = 205.0
        payload3 = {"action": "START", "type": "SENSOR_SPOOFING", "config": {"target": "Bus_4"}}
        self.twin.handle_attack_cmd(payload3)
        self.assertNotIn("Bus_4", self.twin.active_compromises)
        self.twin.publisher.publish_event.assert_called_with(
            source="ATTACK_ORCHESTRATOR",
            event_desc="Attack start BLOCKED: rate limit of 2 attacks per 10 seconds exceeded.",
            severity="WARNING"
        )
        
        # 4. Try again after 10s from first attack (t=210.1) -> should be allowed
        mock_time.return_value = 210.1
        self.twin.handle_attack_cmd(payload3)
        self.assertIn("Bus_4", self.twin.active_compromises)

    @patch("time.time")
    def test_duplicate_suppression(self, mock_time):
        """Verifies duplicate suppression for both control commands and attack payloads."""
        # A. Control command duplicate suppression
        mock_time.return_value = 300.0
        self.twin.last_commands.clear()
        self.twin.breakers["L4_5"] = "CLOSED"
        
        # First operator control
        self.twin.handle_control_cmd("L4_5", "OPEN", {"source": "OPERATOR"})
        self.assertEqual(self.twin.breakers["L4_5"], "OPEN")
        
        # Reset mock call count to track duplicate suppression
        self.twin.publisher.publish_event.reset_mock()
        
        # Identical control command at t=301.0 -> suppressed (no log / action)
        mock_time.return_value = 301.0
        self.twin.handle_control_cmd("L4_5", "OPEN", {"source": "OPERATOR"})
        self.twin.publisher.publish_event.assert_not_called()
        
        # Different control command at t=302.0 -> not suppressed by duplicates (but blocked by cooldown)
        mock_time.return_value = 302.0
        self.twin.handle_control_cmd("L4_5", "CLOSE", {"source": "OPERATOR"})
        self.twin.publisher.publish_event.assert_called_with(
            source="SCADA_GATEWAY",
            event_desc="Control command BLOCKED: Breaker 'L4_5' cooldown active.",
            severity="WARNING"
        )
        
        # B. Attack command duplicate suppression
        self.twin.last_commands.clear()
        self.twin.active_compromises.clear()
        self.twin.attack_rate_limit_bucket.clear()
        mock_time.return_value = 300.0
        
        # First attack
        payload = {"action": "START", "type": "FDIA", "config": {"target": "Bus_5", "bias": 0.1}}
        self.twin.handle_attack_cmd(payload)
        self.assertIn("Bus_5", self.twin.active_compromises)
        
        # Reset mock
        self.twin.publisher.publish_event.reset_mock()
        self.twin.active_compromises.clear()
        
        # Identical attack command at t=301.0 -> suppressed
        mock_time.return_value = 301.0
        self.twin.handle_attack_cmd(payload)
        self.assertNotIn("Bus_5", self.twin.active_compromises)
        self.twin.publisher.publish_event.assert_not_called()

    @patch("time.time")
    def test_advanced_timeline_delays(self, mock_time):
        """Verifies scenario wave scheduling, depends_on triggers, depends_on_grid state check, and local delays."""
        mock_time.return_value = 400.0
        self.twin.active_attack = None
        self.twin.active_scenario = None
        self.twin.prev_telemetry = None
        
        # Start scenario cascading_wave_attack
        payload = {
            "action": "START_SCENARIO",
            "scenario_name": "cascading_wave_attack"
        }
        self.twin.handle_attack_cmd(payload)
        self.assertEqual(self.twin.active_attack, "SCENARIO")
        self.assertEqual(self.twin.active_scenario["name"], "cascading_wave_attack")
        
        # Sweep at t=0
        self.twin.run_simulation_sweep()
        # Stage 1 (wave1_spoof) should be activated (wave 1, time 0)
        stages = self.twin.active_scenario["stages"]
        self.assertTrue(stages[0].get("activated", False))
        self.assertFalse(stages[1].get("activated", False))
        self.assertFalse(stages[2].get("activated", False))
        
        # Advance scenario time to 5.0s, run sweep
        self.twin.scenario_elapsed_time = 5.0
        self.twin.run_simulation_sweep()
        # Stage 2 (wave2_breaker) should now be activated (depends_on wave1_spoof, time=5)
        self.assertTrue(stages[1].get("activated", False))
        self.assertFalse(stages[2].get("activated", False))
        self.assertEqual(self.twin.breakers["L4_5"], "OPEN")
        
        # Run sweep to generate prev_telemetry
        self.twin.run_simulation_sweep()
        self.assertIsNotNone(self.twin.prev_telemetry)
        
        # Manually force undervoltage condition on Bus_5 in prev_telemetry to satisfy depends_on_grid
        self.twin.prev_telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.90
        
        # Run sweep at t=410.0. The undervoltage meets grid condition, trigger recorded
        mock_time.return_value = 410.0
        self.twin.run_simulation_sweep()
        # wave3_cascade has delay=3.0, so it shouldn't activate yet
        self.assertFalse(stages[2].get("activated", False))
        self.assertEqual(self.twin.stage_trigger_times["wave3_cascade"], 410.0)
        
        # Advance time by 2.0s -> should still not be activated
        mock_time.return_value = 412.0
        self.twin.prev_telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.90
        self.twin.run_simulation_sweep()
        self.assertFalse(stages[2].get("activated", False))
        
        # Advance time by 3.5s (t=413.5, which is > 3.0s delay) -> should be activated
        mock_time.return_value = 413.5
        self.twin.prev_telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.90
        self.twin.run_simulation_sweep()
        self.assertTrue(stages[2].get("activated", False))
        self.assertIn("Bus_6", self.twin.active_compromises)

    @patch("time.time")
    def test_restoration_aware_attacker_l7_8(self, mock_time):
        """Tests that attacker intercepts tie-breaker CLOSE attempts and schedules a re-trip."""
        mock_time.return_value = 500.0
        self.twin.active_attack = "FDIA"  # Active attack is required
        self.twin.breakers["L7_8"] = "OPEN"
        self.twin.scheduled_actions.clear()
        
        # Operator attempts restoration:CLOSE
        self.twin.handle_control_cmd("L7_8", "CLOSE", {"source": "OPERATOR"})
        self.assertEqual(self.twin.breakers["L7_8"], "CLOSED")
        
        # Re-trip should be scheduled in 1.0s (at t=501.0)
        self.assertEqual(len(self.twin.scheduled_actions), 1)
        self.assertEqual(self.twin.scheduled_actions[0][0], 501.0)
        self.assertEqual(self.twin.scheduled_actions[0][1], "L7_8")
        self.assertEqual(self.twin.scheduled_actions[0][2], "OPEN")
        
        # Run sweep before 1.0s (at t=500.5) -> should still be CLOSED
        mock_time.return_value = 500.5
        self.twin.run_simulation_sweep()
        self.assertEqual(self.twin.breakers["L7_8"], "CLOSED")
        
        # Run sweep after 1.0s (at t=501.1) -> should be re-tripped OPEN
        mock_time.return_value = 501.1
        self.twin.run_simulation_sweep()
        self.assertEqual(self.twin.breakers["L7_8"], "OPEN")

    def test_validation_window_persistence(self):
        """Verifies PhysicsValidationEngine anomaly and impossible state rolling window persistence."""
        engine = PhysicsValidationEngine()
        
        # Mock dependencies to isolate telemetry validation checks
        engine.physics_filter = MagicMock()
        engine.trust_engine = MagicMock()
        engine.adaptive_filter = MagicMock()
        
        # Nominals
        engine.physics_filter.validate.return_value = {
            "physics_anomaly_score": 5.0,
            "impossible_state": False,
            "impossible_violations": [],
            "kcl_error": 0.5,
            "kvl_error": 0.01
        }
        engine.trust_engine.get_scores.return_value = {
            "bus_trust": {f"Bus_{i}": 100.0 for i in range(1, 10)},
            "line_trust": {},
            "details": {}
        }
        engine.trust_engine.trust_scores = {f"Bus_{i}": 1.0 for i in range(1, 10)}
        engine.adaptive_filter.filter.return_value = ({}, {})
        
        telemetry = {
            "state": {
                "buses": {f"Bus_{i}": {"voltage_pu": 1.0} for i in range(1, 10)},
                "lines": {},
                "breakers": {}
            }
        }
        mock_client = MagicMock()
        
        # Sweep 1: Normal
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 2: Anomalous score = 35. With window length < 3, it fallbacks to current (True) -> SUSPICIOUS
        engine.physics_filter.validate.return_value["physics_anomaly_score"] = 35.0
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "SUSPICIOUS")
        
        # Sweep 3: Nominal (score = 10)
        engine.physics_filter.validate.return_value["physics_anomaly_score"] = 10.0
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 4: Anomalous (1st consecutive) -> persistent_anomaly = False (buffer has [True, False, True]) -> NORMAL
        engine.physics_filter.validate.return_value["physics_anomaly_score"] = 35.0
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 5: Anomalous (2nd consecutive) -> persistent_anomaly = False (buffer has [False, True, True]) -> NORMAL
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 6: Anomalous (3rd consecutive) -> persistent_anomaly = True (buffer [True, True, True]) -> SUSPICIOUS
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "SUSPICIOUS")
        
        # ==========================================
        # Impossible state persistence checks
        # ==========================================
        engine.anomaly_buffer.clear()
        engine.impossible_buffer.clear()
        engine.physics_filter.validate.return_value["physics_anomaly_score"] = 5.0
        
        # Sweep 7: impossible_state = True. len < 3 fallback -> IMPOSSIBLE_STATE
        engine.physics_filter.validate.return_value["impossible_state"] = True
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "IMPOSSIBLE_STATE")
        
        # Sweep 8: impossible_state = False -> NORMAL
        engine.physics_filter.validate.return_value["impossible_state"] = False
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 9: impossible_state = True (1st consecutive). len = 3, buffer has False -> NORMAL
        engine.physics_filter.validate.return_value["impossible_state"] = True
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 10: impossible_state = True (2nd consecutive) -> NORMAL
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "NORMAL")
        
        # Sweep 11: impossible_state = True (3rd consecutive) -> IMPOSSIBLE_STATE
        engine.process_telemetry(telemetry, mock_client)
        published_payload = json.loads(mock_client.publish.call_args_list[-3][0][1])
        self.assertEqual(published_payload["physics_state"], "IMPOSSIBLE_STATE")

if __name__ == "__main__":
    unittest.main()
