import os
import sys
import unittest
import json
from unittest.mock import MagicMock

# Setup path so we can import core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.arena.red_agent import RedAgent
from core.arena.blue_agent import BlueAgent
from core.arena.arena_simulator import ArenaSimulator
from core.arena.arena_memory import ArenaMemory
from core.arena.arena_coordinator import ArenaCoordinator

class TestArenaCoevolution(unittest.TestCase):
    def setUp(self):
        self.dummy_telemetry = {
            "timestamp": 1700000000000,
            "state": {
                "buses": {f"Bus_{i}": {"voltage_pu": 1.0, "frequency_hz": 60.0} for i in range(1, 10)}
            }
        }

    def test_red_agent_learning(self):
        """Verifies RedAgent action selection, Q-table registration, and exploration decay."""
        agent = RedAgent(epsilon=0.5)
        blue_posture = {
            "anomaly_threshold": 0.4,
            "trust_decay_speed": "FAST"
        }

        # Select action
        idx, action = agent.select_action(blue_posture)
        self.assertGreaterEqual(idx, 0)
        self.assertLess(idx, len(agent.actions))
        self.assertEqual(len(action), 4)

        # Update Q-value
        state_key = agent.get_state_key(blue_posture)
        self.assertIn(state_key, agent.q_table)
        
        agent.update_q_value(blue_posture, idx, 10.0, blue_posture)
        self.assertGreater(agent.q_table[state_key][idx], 0.0)

        # Epsilon decay
        old_eps = agent.epsilon
        agent.decay_exploration()
        self.assertLess(agent.epsilon, old_eps)

    def test_blue_agent_learning(self):
        """Verifies BlueAgent action selection, Q-table registration, and exploration decay."""
        agent = BlueAgent(epsilon=0.5)
        red_attack = {
            "target": "Bus_5",
            "severity": 0.8
        }

        idx, action = agent.select_action(red_attack)
        self.assertGreaterEqual(idx, 0)
        self.assertLess(idx, len(agent.actions))
        self.assertEqual(len(action), 4)

        state_key = agent.get_state_key(red_attack)
        self.assertIn(state_key, agent.q_table)

        agent.update_q_value(red_attack, idx, -5.0, red_attack)
        self.assertLess(agent.q_table[state_key][idx], 0.0)

    def test_arena_simulator(self):
        """Verifies simulator outputs correctness and response delays calculations."""
        simulator = ArenaSimulator()
        red_action = ("Bus_5", "FDIA_ESCALATION", 0.8, 0.3)
        blue_action = (0.5, "FAST", 30.0, "REDUNDANT_PATH")

        results = simulator.run_match(red_action, blue_action)
        
        self.assertTrue("detection_delay" in results)
        self.assertTrue("containment_delay" in results)
        self.assertTrue("restoration_delay" in results)
        self.assertTrue("voltage_deviation" in results)
        self.assertTrue("frequency_deviation" in results)
        self.assertTrue("mitigation_success" in results)
        self.assertTrue("events" in results)
        self.assertTrue("telemetry" in results)

        self.assertGreater(results["detection_delay"], 0.0)
        self.assertGreater(results["containment_delay"], 0.0)
        self.assertGreater(results["restoration_delay"], 0.0)
        self.assertGreaterEqual(results["voltage_deviation"], 0.0)
        self.assertLessEqual(results["voltage_deviation"], 0.35)

    def test_arena_memory_io(self):
        """Checks recording match outcomes, memory dump saves, and reload cycles."""
        memory = ArenaMemory(persistence_file="test_arena_memory.json")
        
        red_act = {"target": "Bus_5", "severity": 0.8, "stealth": 0.3, "type": "FDIA_ESCALATION"}
        blue_act = {"anomaly_threshold": 0.5, "trust_decay_speed": "FAST", "rollback_lockout": 30.0, "routing_strategy": "REDUNDANT_PATH"}
        results = {"voltage_deviation": 0.1, "mitigation_success": True}

        memory.record_match(1, red_act, blue_act, results, 1.5, 4.2)
        self.assertEqual(len(memory.history), 1)

        # Save & Load back
        dummy_red_q = {"LOW_FAST": [1.0, 2.0]}
        dummy_blue_q = {"Bus_5_HIGH": [0.5, 1.5]}
        memory.save_state(dummy_red_q, dummy_blue_q)

        # Clean file exists
        self.assertTrue(os.path.exists(memory.persistence_path))

        # Load
        new_mem = ArenaMemory(persistence_file="test_arena_memory.json")
        loaded = new_mem.load_state()
        
        self.assertEqual(loaded["red_q_table"], dummy_red_q)
        self.assertEqual(loaded["blue_q_table"], dummy_blue_q)
        self.assertEqual(len(loaded["history"]), 1)

        # Cleanup test files
        if os.path.exists(memory.persistence_path):
            os.remove(memory.persistence_path)

    def test_arena_coordinator_flow(self):
        """Asserts coordinator running simulation round, throttling, and publishing to MQTT."""
        coordinator = ArenaCoordinator()
        client_mock = MagicMock()

        # Call match round directly
        coordinator.run_match_round(client_mock)

        # Verifies 4 topics are published (match, rewards, evolution, recommendations)
        self.assertEqual(client_mock.publish.call_count, 4)

        # Test throttling
        coordinator.last_cycle_time = 9999999999.0 # mock future time to block cycles
        coordinator.handle_telemetry(self.dummy_telemetry, client_mock)
        # Should not publish anything extra due to throttling
        self.assertEqual(client_mock.publish.call_count, 4)

        # Test duplicate packets filter
        coordinator.last_cycle_time = 0.0
        coordinator.last_telemetry_timestamp = 1700000000000
        coordinator.handle_telemetry(self.dummy_telemetry, client_mock)
        # Should not publish anything extra due to timestamp <= last timestamp
        self.assertEqual(client_mock.publish.call_count, 4)

        # Clean up coordination test persistence if any
        if os.path.exists(coordinator.memory.persistence_path):
            os.remove(coordinator.memory.persistence_path)

if __name__ == "__main__":
    unittest.main()
