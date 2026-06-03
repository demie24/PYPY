import os
import sys
import unittest
import time
from unittest.mock import MagicMock

# Setup path so we can import core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.ai_prediction.predictive_defense_engine import PredictiveDefenseEngine

class TestPredictiveDefense(unittest.TestCase):
    def setUp(self):
        self.engine = PredictiveDefenseEngine(history_len=5)
        self.client_mock = MagicMock()

        # Build simple mock telemetry
        self.telemetry = {
            "timestamp": 1700000000000,
            "state": {
                "buses": {f"Bus_{i}": {"voltage_pu": 1.0, "frequency_hz": 60.0} for i in range(1, 10)},
                "lines": {l: {"capacity_pct": 50.0, "current_pu": 0.5} for l in [
                    "L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"
                ]},
                "breakers": {l: "CLOSED" for l in [
                    "L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"
                ]}
            },
            "attack_status": {
                "active_attack": None,
                "compromised_nodes": {}
            }
        }

    def test_threat_escalation_low(self):
        """Verifies threat forecasting is LOW under nominal conditions."""
        self.engine.latest_threat = {"threat_score": 10.0}
        self.engine.threat_history.append((time.time() - 2.0, 10.0))
        self.engine.threat_history.append((time.time() - 1.0, 10.0))
        self.engine.threat_history.append((time.time(), 10.0))
        
        forecast = self.engine.forecast_threat_escalation()
        self.assertEqual(forecast["projected_severity"], "LOW")
        self.assertEqual(forecast["escalation_probability"], 0.0)

    def test_threat_escalation_critical(self):
        """Asserts that threat score escalation projects severe status and escalates probability."""
        self.engine.latest_threat = {"threat_score": 60.0}
        
        # Simulating rapid growth of threat score (e.g. +3 score per second)
        now = time.time()
        self.engine.threat_history.append((now - 4.0, 48.0))
        self.engine.threat_history.append((now - 2.0, 54.0))
        self.engine.threat_history.append((now, 60.0))
        
        forecast = self.engine.forecast_threat_escalation()
        self.assertEqual(forecast["projected_severity"], "CRITICAL")
        self.assertGreater(forecast["escalation_probability"], 0.50)

    def test_pre_attack_early_warning_active(self):
        """Verifies early warnings trigger on suspicious patterns."""
        self.engine.latest_telemetry = self.telemetry
        self.telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.90
        self.engine.latest_trust = {
            "details": {
                "Bus_5": {"trust_score": 50.0},
                "Bus_6": {"trust_score": 60.0}
            }
        }
        self.engine.alert_history.append({"type": "PHYSICS_KCL_VIOLATION"})
        self.engine.alert_history.append({"type": "PHYSICS_KVL_VIOLATION"})
        
        warning = self.engine.evaluate_pre_attack_patterns()
        self.assertTrue(warning["early_warning_active"])
        self.assertGreater(warning["pre_attack_likelihood"], 0.40)
        self.assertIn("TRUST_SCORE_DEGRADATION", warning["active_indicators"])
        self.assertIn("PHYSICS_VALIDATION_FAILURES", warning["active_indicators"])

    def test_predictive_risk_scoring(self):
        """Verifies risk calculation details and priority weights."""
        self.engine.latest_telemetry = self.telemetry
        self.engine.latest_ai_threat_forecast = {
            "cyber_instability_probability": 0.80
        }
        
        # Induce heavy physical stress on Bus_5 (hospital)
        self.telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.90
        
        risk = self.engine.compute_predictive_risk()
        self.assertGreater(risk["node_risk_scores"]["Bus_5"], 60.0)
        self.assertEqual(risk["topology_risk_score"], 0.0)

    def test_predictive_defense_advisor(self):
        """Checks preventative advice generation and Malay/English rationales."""
        warning = {
            "pre_attack_likelihood": 0.70,
            "active_indicators": ["TRUST_SCORE_DEGRADATION"]
        }
        risk = {
            "restoration_risk_score": 75.0,
            "node_risk_scores": {"Bus_5": 85.0}
        }
        
        recs = self.engine.generate_preventive_advice(warning, risk)
        
        actions = [r["action"] for r in recs]
        self.assertIn("INCREASE_TELEMETRY_VALIDATION_FREQUENCY", actions)
        self.assertIn("ISOLATE_VULNERABLE_NODE", actions)
        self.assertIn("DELAY_RISKY_RESTORATIONS", actions)
        
        # Verify language rationales
        for r in recs:
            self.assertIn("rationale", r)
            self.assertIn("rationale_ms", r)
            self.assertIn("expected_benefits", r)
            self.assertIn("risk_assessment", r)

    def test_incident_memory_recurrence(self):
        """Tests learning from repeated incidents in event history."""
        self.engine.latest_telemetry = self.telemetry
        self.engine.event_history.append({"event": "Attack active on Bus_5", "severity": "CRITICAL"})
        self.engine.event_history.append({"event": "Attack active on Bus_5", "severity": "CRITICAL"})
        self.engine.event_history.append({"event": "Failed to reconnect line L4_5", "severity": "WARNING"})
        
        self.engine.analyze_incident_memory()
        
        self.assertEqual(self.engine.attack_recurrence.get("Bus_5"), 2)
        self.assertIn("L4_5", self.engine.failed_restorations)

    def test_flood_control_and_ordering(self):
        """Ensures that out-of-order packets are dropped and flood throttling is enforced."""
        self.engine.latest_telemetry = self.telemetry
        self.engine.last_telemetry_timestamp = 1000
        
        # Discard duplicate or older packet
        self.engine.handle_telemetry({"timestamp": 900, "state": {}}, self.client_mock)
        self.client_mock.publish.assert_not_called()
        
        # Enforce cycle throttling (less than 0.5s interval)
        self.engine.last_cycle_time = time.time()
        self.engine.handle_telemetry({"timestamp": 1200, "state": {}}, self.client_mock)
        self.client_mock.publish.assert_not_called()

    def test_graceful_degradation_fallback(self):
        """Tests that forecasting falls back gracefully when LSTM prediction cache is empty."""
        self.engine.latest_telemetry = self.telemetry
        self.engine.latest_threat = None
        self.engine.latest_trust = None
        self.engine.latest_ai_threat_forecast = None
        
        # Should fit and run without throwing errors
        self.engine.execute_fusion(self.client_mock)
        self.assertEqual(self.client_mock.publish.call_count, 6)

if __name__ == "__main__":
    unittest.main()
