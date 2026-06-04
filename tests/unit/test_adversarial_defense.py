import os
import sys
import unittest
import time
from unittest.mock import MagicMock

# Setup path so we can import core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.adversarial.attack_pattern_generator import AttackPatternGenerator
from core.adversarial.defense_evaluator import DefenseEvaluator
from core.adversarial.resilience_scorer import ResilienceScorer
from core.adversarial.campaign_simulator import CampaignSimulator
from core.adversarial.adversarial_memory import AdversarialMemory
from core.adversarial.adversarial_coordinator import AdversarialCoordinator

class TestAdversarialDefense(unittest.TestCase):
    def setUp(self):
        self.telemetry = {
            "timestamp": 1700000000000,
            "state": {
                "buses": {f"Bus_{i}": {"voltage_pu": 1.0, "frequency_hz": 60.0} for i in range(1, 10)},
                "lines": {l: {"capacity_pct": 50.0, "current_pu": 0.5} for l in [
                    "L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"
                ]}
            }
        }
        self.threat_data = {"threat_score": 10.0}

    def test_campaign_generation(self):
        """Verifies that realistic attack campaigns are correctly formatted."""
        generator = AttackPatternGenerator()
        
        # Test FDIA
        camp = generator.generate_campaign("FDIA_ESCALATION", "Bus_5")
        self.assertEqual(camp["campaign_type"], "FDIA_ESCALATION")
        self.assertEqual(camp["target"], "Bus_5")
        self.assertEqual(camp["severity"], 0.80)
        self.assertEqual(camp["stealth_score"], 0.35)
        self.assertTrue(len(camp["attack_sequence"]) > 0)
        self.assertTrue("campaign_id" in camp)

        # Test invalid type fallback
        camp_fallback = generator.generate_campaign("INVALID_TYPE")
        self.assertEqual(camp_fallback["campaign_type"], "TELEMETRY_MANIPULATION")

    def test_defense_evaluator(self):
        """Verifies correct timing calculations for defense reactions."""
        evaluator = DefenseEvaluator()
        campaign = {
            "campaign_id": "CAMP_TEST",
            "timestamp": 1000000, # 1000.0s
            "campaign_type": "FDIA_ESCALATION"
        }

        # Setup timelines
        events = [
            {"timestamp": 1001000, "event": "GRID_ATTACK: Exploited Bus_5 sensor validation"},
            {"timestamp": 1004000, "event": "ANOMALY DETECTED: Cyber threat score high"},
            {"timestamp": 1010000, "event": "GRID ISOLATED: Breaker control activated"},
            {"timestamp": 1025000, "event": "NORMAL OPERATIONS: Grid topology restored"}
        ]

        metrics = evaluator.evaluate_defense(campaign, events)
        
        self.assertEqual(metrics["campaign_id"], "CAMP_TEST")
        # 1004 - 1000 = 4.0s detection delay
        self.assertEqual(metrics["detection_delay"], 4.0)
        # 1010 - 1004 = 6.0s containment delay
        self.assertEqual(metrics["containment_delay"], 6.0)
        # 1025 - 1010 = 15.0s restoration delay
        self.assertEqual(metrics["restoration_delay"], 15.0)
        self.assertTrue(metrics["mitigation_success"])
        self.assertGreater(metrics["overall_defense_rating"], 0.80)

    def test_resilience_scorer(self):
        """Checks cyber, recovery, trust, and operational resilience scorer logic."""
        scorer = ResilienceScorer()
        eval_metrics = {
            "detection_accuracy": 1.0,
            "detection_delay": 5.0,
            "containment_delay": 10.0,
            "restoration_delay": 15.0,
            "trust_recovery_time": 30.0,
            "mitigation_success": True
        }

        # Perfect telemetry history
        res = scorer.calculate_resilience(eval_metrics, [self.telemetry])
        
        self.assertGreater(res["cyber_resilience"], 0.80)
        self.assertGreater(res["recovery_resilience"], 0.70)
        self.assertGreater(res["trust_resilience"], 0.70)
        self.assertEqual(res["operational_resilience"], 1.0)
        self.assertGreater(res["overall_resilience_score"], 0.80)

        # Degraded telemetry history (voltage deviation)
        bad_telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 0.82, "frequency_hz": 60.0}
                }
            }
        }
        res_bad = scorer.calculate_resilience(eval_metrics, [bad_telemetry])
        self.assertLess(res_bad["operational_resilience"], 1.0)

    def test_campaign_simulator(self):
        """Verifies simulated timeline state progression under campaign simulation."""
        simulator = CampaignSimulator()
        generator = AttackPatternGenerator()
        
        camp = generator.generate_campaign("FDIA_ESCALATION", "Bus_5")
        sim_res = simulator.simulate_campaign(camp, {})

        self.assertTrue("simulated_events" in sim_res)
        self.assertTrue("simulated_telemetry" in sim_res)
        self.assertTrue(len(sim_res["simulated_events"]) > 0)
        self.assertTrue(len(sim_res["simulated_telemetry"]) > 0)

    def test_adversarial_memory(self):
        """Checks outcomes recording, memory load/save, and weakness summaries."""
        memory = AdversarialMemory(persistence_file="dummy_adversarial_memory.json")
        
        campaign = {"campaign_id": "CAMP_1", "campaign_type": "FDIA_ESCALATION", "target": "Bus_5", "timestamp": 1000000}
        eval_metrics = {"detection_delay": 4.0, "containment_delay": 6.0, "restoration_delay": 25.0, "mitigation_success": False}
        resilience = {"overall_resilience_score": 0.50}

        memory.record_simulation(campaign, eval_metrics, resilience)

        summary = memory.get_weakness_summary()
        self.assertIn("Bus_5", [n["node"] for n in summary["high_risk_nodes"]])
        self.assertIn("Bus_5", [n["path_or_node"] for n in summary["slow_recovery_paths"]])

    def test_coordinator_cycle_publishing(self):
        """Asserts coordinator running simulation cycle triggers MQTT publishes."""
        coordinator = AdversarialCoordinator()
        client_mock = MagicMock()

        coordinator.latest_telemetry = self.telemetry
        coordinator.latest_threat = self.threat_data

        coordinator.run_adversarial_cycle(client_mock)

        # Verifies 4 calls to publish strategic adversarial topics
        self.assertEqual(client_mock.publish.call_count, 4)

if __name__ == "__main__":
    unittest.main()
