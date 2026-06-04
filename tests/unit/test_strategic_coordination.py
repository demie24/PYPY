import os
import sys
import unittest
import time
from unittest.mock import MagicMock

# Setup path so we can import core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.strategy.strategy_memory import StrategyMemory
from core.strategy.priority_engine import PriorityEngine
from core.strategy.resource_allocator import ResourceAllocator
from core.strategy.impact_estimator import ImpactEstimator
from core.strategy.action_simulator import ActionSimulator
from core.strategy.strategic_coordinator import StrategicCoordinator

class TestStrategicCoordination(unittest.TestCase):
    def setUp(self):
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
        self.threat_data = {"threat_score": 10.0}
        self.future_risk = {
            "node_risk_scores": {f"Bus_{i}": 10.0 for i in range(1, 10)},
            "asset_risk_scores": {"L4_5": 10.0},
            "cyber_physical_instability_risk": {"future_risk": 20.0}
        }

    def test_priority_engine_ranking(self):
        """Verifies correct ranking order of concurrent grid incidents."""
        engine = PriorityEngine()
        
        # Scenario 1: Nominal monitoring
        priorities = engine.evaluate_priorities(self.telemetry, self.threat_data, [])
        self.assertEqual(priorities, ["NOMINAL_MONITORING"])

        # Scenario 2: Cyber attack and Line Overload
        self.telemetry["attack_status"]["active_attack"] = "FDIA"
        alerts = [{"type": "LINE_OVERLOAD_WARNING"}]
        self.telemetry["state"]["lines"]["L1_4"]["capacity_pct"] = 110.0
        
        priorities = engine.evaluate_priorities(self.telemetry, self.threat_data, alerts)
        self.assertEqual(priorities, ["CYBER_ATTACK", "LINE_OVERLOAD"])

        # Scenario 3: Voltage Collapse priority
        self.telemetry["attack_status"]["active_attack"] = None
        self.telemetry["state"]["lines"]["L1_4"]["capacity_pct"] = 50.0
        self.telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.85
        priorities = engine.evaluate_priorities(self.telemetry, self.threat_data, [])
        self.assertEqual(priorities, ["VOLTAGE_COLLAPSE"])

    def test_resource_allocation(self):
        """Checks operator dispatching, backup line utilization, and relay allocation."""
        allocator = ResourceAllocator(max_operators=3, max_relays=4, backup_lines=["L7_8"])
        
        # Test allocation on line overload and cyber attack
        priority_order = ["CYBER_ATTACK", "LINE_OVERLOAD"]
        risk_data = {
            "node_risk_scores": {"Bus_5": 70.0},
            "asset_risk_scores": {"L1_4": 80.0}
        }
        
        alloc = allocator.allocate_resources(priority_order, risk_data)
        
        # Dispatched operators to Bus_5 and L1_4
        self.assertIn("Bus_5", alloc["dispatched_operators"])
        self.assertIn("L1_4", alloc["dispatched_operators"])
        self.assertEqual(alloc["available_operators_remaining"], 1)

        # Rerouted via backup line
        self.assertIn("L7_8", alloc["reserved_backup_lines"])
        self.assertEqual(len(alloc["available_backup_lines_remaining"]), 0)

        # Allocated safety relays to Bus_5
        self.assertIn("Bus_5", alloc["allocated_relays"])
        self.assertEqual(alloc["available_relays_remaining"], 3)
        self.assertTrue(len(alloc["allocation_rationale"]) > 0)

    def test_action_simulation_scores(self):
        """Ensures ActionSimulator produces candidate actions with valid metrics."""
        simulator = ActionSimulator()
        candidates = simulator.simulate_candidates(self.telemetry, self.threat_data, [], self.future_risk)
        
        actions = [c["action"] for c in candidates]
        self.assertIn("ISOLATE_BUS_5", actions)
        self.assertIn("PREEMPTIVE_REROUTE", actions)
        
        for c in candidates:
            self.assertTrue(0.0 <= c["risk_score"] <= 1.0)
            self.assertTrue(0.0 <= c["benefit_score"] <= 1.0)
            self.assertTrue(0.0 <= c["stability_score"] <= 1.0)

    def test_impact_estimation(self):
        """Asserts pre-execution consequence calculations scaled by strategy memory."""
        estimator = ImpactEstimator()
        
        # No history metrics (100% success default confidence)
        metrics = {"success_rate": 1.0, "rollback_rate": 0.0, "total_count": 0}
        priority_order = ["LINE_OVERLOAD"]
        risk_data = {}
        
        est = estimator.estimate_impact("PREEMPTIVE_REROUTE", metrics, priority_order, risk_data)
        self.assertEqual(est["action"], "PREEMPTIVE_REROUTE")
        self.assertGreater(est["predicted_stability_gain"], 0.30)
        self.assertGreater(est["predicted_risk_reduction"], 0.40)
        self.assertEqual(est["confidence"], 0.99)

        # Degraded history metrics
        bad_metrics = {"success_rate": 0.40, "rollback_rate": 0.50, "total_count": 10}
        est_bad = estimator.estimate_impact("PREEMPTIVE_REROUTE", bad_metrics, priority_order, risk_data)
        self.assertLess(est_bad["confidence"], 0.30)
        self.assertLess(est_bad["predicted_stability_gain"], est["predicted_stability_gain"])

    def test_strategy_memory_recording(self):
        """Verifies success/failure recording, rates calculation, and mock save."""
        memory = StrategyMemory(persistence_file="dummy_memory.json")
        
        # Record 2 successes, 1 rollback failure
        memory.record_action("PREEMPTIVE_REROUTE", success=True, rolled_back=False)
        memory.record_action("PREEMPTIVE_REROUTE", success=True, rolled_back=False)
        memory.record_action("PREEMPTIVE_REROUTE", success=False, rolled_back=True)

        metrics = memory.get_metrics("PREEMPTIVE_REROUTE")
        self.assertEqual(metrics["total_count"], 3)
        self.assertEqual(metrics["success_rate"], 0.67)
        self.assertEqual(metrics["rollback_rate"], 0.33)

        # Empty action check
        empty = memory.get_metrics("NON_EXISTENT")
        self.assertEqual(empty["success_rate"], 1.0)
        self.assertEqual(empty["rollback_rate"], 0.0)

    def test_coordinator_cycle_publishing(self):
        """Tests coordinator cycle completes and triggers MQTT publishes."""
        coordinator = StrategicCoordinator()
        client_mock = MagicMock()
        
        coordinator.latest_telemetry = self.telemetry
        coordinator.latest_threat = self.threat_data
        coordinator.latest_prediction_future_risk = self.future_risk
        
        coordinator.run_coordination_cycle(client_mock)
        
        # Verify 4 calls to publish strategy topics
        self.assertEqual(client_mock.publish.call_count, 4)

    def test_coordinator_feedback_processing(self):
        """Verifies event monitoring processes outcomes back into StrategyMemory."""
        coordinator = StrategicCoordinator()
        coordinator.memory = StrategyMemory(persistence_file="dummy_memory.json")
        
        # Event showing success
        event_ok = {"event": "Strategic action PREEMPTIVE_REROUTE completed successfully."}
        coordinator.process_feedback_events(event_ok)
        metrics = coordinator.memory.get_metrics("PREEMPTIVE_REROUTE")
        self.assertEqual(metrics["total_count"], 1)
        self.assertEqual(metrics["success_rate"], 1.0)

        # Event showing failure rollback
        event_fail = {"event": "Critical rollback occurred on PREEMPTIVE_REROUTE execution."}
        coordinator.process_feedback_events(event_fail)
        metrics = coordinator.memory.get_metrics("PREEMPTIVE_REROUTE")
        self.assertEqual(metrics["total_count"], 2)
        self.assertEqual(metrics["success_rate"], 0.50)
        self.assertEqual(metrics["rollback_rate"], 0.50)

if __name__ == "__main__":
    unittest.main()
