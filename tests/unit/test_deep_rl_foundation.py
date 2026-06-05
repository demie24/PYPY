import os
import sys
import unittest
import numpy as np
import shutil

# Setup path so we can import research modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl")))

from research.deep_rl.environment import SmartGridRLEnv
from research.deep_rl.state_encoder import StateEncoder
from research.deep_rl.reward_engine import RewardEngine
from research.deep_rl.experience_buffer import ExperienceBuffer
from research.deep_rl.model_manager import ModelManager
from research.deep_rl.training_runner import TrainingRunner

class DummyAgent:
    def __init__(self):
        self.transitions = []

    def select_action(self, state):
        return {
            "target": "Bus_5",
            "severity": 0.3,
            "attack_type": "FDIA",
            "stealth": 0.8,
            "routing_strategy": "REDUNDANT_PATH",
            "rollback_lockout": 30.0,
            "anomaly_threshold": 0.4
        }

    def remember(self, state, action, reward, next_state, done):
        self.transitions.append((state, action, reward, next_state, done))

    def learn(self, state, action, reward, next_state, done):
        pass

class TestDeepRLFoundation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_rl_test"))
        os.makedirs(self.temp_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_environment_lifecycle(self):
        """Verifies environment reset, step transitions, and terminal checks."""
        env = SmartGridRLEnv(max_steps=5, bus_count=9)
        
        # Test reset
        state = env.reset()
        self.assertEqual(len(state["buses"]), 9)
        self.assertEqual(env.current_step, 0)
        self.assertFalse(env.is_terminal())

        # Test step
        action = {
            "red": {"target": "Bus_5", "severity": 0.8, "attack_type": "FDIA", "stealth": 0.2},
            "blue": {"routing_strategy": "REDUNDANT_PATH", "rollback_lockout": 30.0, "anomaly_threshold": 0.4}
        }
        
        next_state, rewards, done, info = env.step(action)
        self.assertEqual(env.current_step, 1)
        self.assertIn("red", rewards)
        self.assertIn("blue", rewards)
        
        # Check that we eventually reach terminal state due to max steps
        for _ in range(10):
            _, _, done, _ = env.step(action)
            if done:
                break
        self.assertTrue(done)

    def test_state_encoder(self):
        """Verifies deterministic fixed-size state vector outputs."""
        encoder = StateEncoder()
        env = SmartGridRLEnv()
        state = env.reset()

        vector1 = encoder.encode(state)
        vector2 = encoder.encode(state)

        # Output shape and type verification
        self.assertEqual(vector1.shape, (encoder.state_dim,))
        self.assertEqual(vector1.dtype, np.float32)
        
        # Deterministic check
        np.testing.assert_array_equal(vector1, vector2)

    def test_reward_engine(self):
        """Verifies correct calculation of Red and Blue team rewards."""
        engine = RewardEngine()
        env = SmartGridRLEnv()
        
        state = env.reset()
        action = {"target": "Bus_5", "severity": 0.8, "attack_type": "FDIA", "stealth": 0.1}
        
        # Simulate transition
        next_state, _, _, _ = env.step({"red": action})

        red_reward = engine.calculate_red_reward(state, action, next_state)
        blue_reward = engine.calculate_blue_reward(state, action, next_state)

        # Red should get positive reward for disruption and stealth
        self.assertGreater(red_reward, 0.0)
        # Blue should receive penalty for deviations
        self.assertLess(blue_reward, 1.0)

    def test_experience_buffer(self):
        """Checks buffer size limits, random sampling, and file persistence."""
        buffer_file = os.path.join(self.temp_dir, "replay_buffer.pkl")
        buf = ExperienceBuffer(capacity=5)

        # Add transitions
        for i in range(10):
            buf.push(f"s_{i}", f"a_{i}", float(i), f"s_next_{i}", False)

        # Capacity limit should restrict size to 5
        self.assertEqual(len(buf), 5)

        # Test sampling
        batch = buf.sample(3)
        self.assertEqual(len(batch), 3)

        # Test saving & loading
        buf.save(buffer_file)
        self.assertTrue(os.path.exists(buffer_file))

        new_buf = ExperienceBuffer()
        new_buf.load(buffer_file)
        self.assertEqual(len(new_buf), 5)
        self.assertEqual(new_buf.buffer[0][0], buf.buffer[0][0])

    def test_model_manager(self):
        """Verifies framework-agnostic checkpoint storage and reloading."""
        checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        manager = ModelManager(base_dir=checkpoint_dir)

        dummy_weights = {"q_table": {"Bus_5": [0.1, 0.2]}}
        metadata = {"layer": "R1", "version": 1.0}
        history = {"loss": [0.5, 0.2]}

        # Save checkpoint
        path = manager.save_checkpoint("v1", dummy_weights, metadata, history)
        self.assertTrue(os.path.exists(path))
        self.assertIn("v1", manager.list_checkpoints())

        # Load checkpoint
        loaded = manager.load_checkpoint("v1")
        self.assertEqual(loaded["weights"], dummy_weights)
        self.assertEqual(loaded["metadata"], metadata)
        self.assertEqual(loaded["training_history"], history)

    def test_training_runner_loop(self):
        """Asserts training coordinator registration and training loops execution."""
        log_dir = os.path.join(self.temp_dir, "logs")
        runner = TrainingRunner(log_dir=log_dir)

        agent = DummyAgent()
        runner.register_agent("red", agent)
        runner.register_agent("blue", agent)

        # Run 1 episode
        ep_summary = runner.run_episode()
        self.assertGreaterEqual(ep_summary["steps"], 1)
        self.assertIn("red", ep_summary["rewards"])
        self.assertIn("blue", ep_summary["rewards"])
        
        # Run loop
        stats = runner.run_training_loop(episodes=3)
        self.assertEqual(stats["episode_count"], 3)
        self.assertEqual(len(stats["rewards_history"]["red"]), 3)
        self.assertGreater(stats["training_duration_sec"], 0.0)

        # Verify logs were saved
        metrics_file = os.path.join(log_dir, "training_metrics.json")
        self.assertTrue(os.path.exists(metrics_file))

if __name__ == "__main__":
    unittest.main()
