import os
import sys
import unittest
import numpy as np
import torch
import shutil

# Setup path so we can import research modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl", "dqn")))

from research.deep_rl.dqn.training_config import DQNConfig
from research.deep_rl.dqn.dqn_network import DQNNetwork
from research.deep_rl.dqn.replay_memory import DQNReplayMemory
from research.deep_rl.dqn.dqn_red_agent import DQNRedAgent
from research.deep_rl.dqn.dqn_blue_agent import DQNBlueAgent
from research.deep_rl.training_runner import TrainingRunner
from research.deep_rl.environment import SmartGridRLEnv

class TestDQNBlueAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_dqn_blue_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        # Create temp dirs for checkpoints and logs
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_dqn_network_forward(self):
        """Verifies network output shape for Blue Team action space size (32)."""
        input_dim = 67
        output_dim = 32
        
        net = DQNNetwork(input_dim, output_dim, hidden_layers=[32, 16], activation="relu", seed=42)
        x = torch.randn(5, input_dim)
        out = net(x)
        self.assertEqual(out.shape, (5, output_dim))

    def test_action_space_encoding_decoding(self):
        """Verifies encoding and decoding logic between discrete actions and Blue dicts."""
        agent = DQNBlueAgent(input_dim=67)
        
        # Verify decoding ranges and mapping keys
        for idx in range(32):
            action_dict = agent._decode_action(idx)
            self.assertIn("routing_strategy", action_dict)
            self.assertIn("anomaly_threshold", action_dict)
            self.assertIn("rollback_lockout", action_dict)
            self.assertIn("trust_decay_speed", action_dict)
            
            # Encode back and verify it resolves back to the same or close action
            encoded_idx = agent._encode_action(action_dict)
            self.assertGreaterEqual(encoded_idx, 0)
            self.assertLess(encoded_idx, 32)

    def test_epsilon_greedy_selection(self):
        """Checks epsilon exploration rate decay and action selection for Blue defender."""
        config = DQNConfig(epsilon_start=1.0, epsilon_end=0.1, epsilon_decay=0.9)
        agent = DQNBlueAgent(config=config, input_dim=67)
        
        self.assertEqual(agent.action_space_size, 32)
        state = np.random.randn(67).astype(np.float32)
        
        # Selecting action should decay epsilon
        action1 = agent.select_action(state, eval_mode=False)
        self.assertLess(agent.epsilon, 1.0)
        self.assertIn("routing_strategy", action1)
        self.assertIn("anomaly_threshold", action1)

        # Force evaluation mode (epsilon shouldn't decay)
        current_eps = agent.epsilon
        action_eval = agent.select_action(state, eval_mode=True)
        self.assertEqual(agent.epsilon, current_eps)

    def test_learn_step_execution(self):
        """Ensures learning step executes correctly, records loss, and updates parameters."""
        config = DQNConfig(batch_size=4, learning_rate=0.01)
        agent = DQNBlueAgent(config=config, input_dim=67)
        
        # Populate replay memory and record metrics
        for _ in range(10):
            # Uniform values around nominal range (e.g. [0.5, 1.5] for voltage/freq, [0.0, 1.0] for others)
            state = np.random.uniform(0.1, 1.0, 67).astype(np.float32)
            next_state = np.random.uniform(0.1, 1.0, 67).astype(np.float32)
            # Make some components represent threat and anomalies to update metrics code paths
            state[3] = 1.0 # threat on Bus_1
            next_state[3] = 0.5 # threat reduced on Bus_1
            next_state[4] = 1.0 # anomaly flag active
            
            action_dict = {"routing_strategy": "DEFAULT", "anomaly_threshold": 0.5}
            agent.remember(state, action_dict, 0.5, next_state, False)

        # Confirm performance metrics track progress
        self.assertGreater(agent.total_steps, 0)
        self.assertGreaterEqual(agent.get_detection_success_rate(), 0.0)
        self.assertGreaterEqual(agent.get_containment_success_rate(), 0.0)
        self.assertGreaterEqual(agent.get_stability_preservation(), 0.0)
        self.assertGreaterEqual(agent.get_trust_preservation(), 0.0)

        # Cache weight before learning
        initial_params = [p.clone() for p in agent.policy_net.parameters()]
        
        # Run training update step
        agent.learn(None, None, None, None, None)
        
        # Verify loss was recorded
        self.assertGreater(len(agent.loss_history), 0)
        self.assertGreater(agent.loss_history[-1], 0.0)

        # Verify weights were updated
        weights_changed = False
        for p_init, p_new in zip(initial_params, agent.policy_net.parameters()):
            if not torch.equal(p_init, p_new):
                weights_changed = True
                break
        self.assertTrue(weights_changed)

    def test_checkpoint_save_load(self):
        """Tests serialization and deserialization of parameters, target weights, and metadata."""
        config = DQNConfig(epsilon_start=0.5, seed=123)
        
        agent = DQNBlueAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir
        
        # Set dummy history/loss metrics
        agent.loss_history = [0.4, 0.2]
        agent.epsilon_history = [0.5, 0.49]
        agent.epsilon = 0.49
        
        # Save model
        chk_path = agent.save_model("test_blue_chk")
        self.assertTrue(os.path.exists(chk_path))

        # Create new agent and reload weights
        new_agent = DQNBlueAgent(config=config, input_dim=67)
        new_agent.model_manager.base_dir = self.checkpoint_dir
        new_agent.load_model("test_blue_chk")

        # Assert parity of state dict params
        for p1, p2 in zip(agent.policy_net.parameters(), new_agent.policy_net.parameters()):
            self.assertTrue(torch.equal(p1, p2))
            
        self.assertEqual(new_agent.epsilon, 0.49)
        self.assertEqual(new_agent.loss_history, [0.4, 0.2])

    def test_coevolution_training_runner_integration(self):
        """Asserts DQN Red Agent vs DQN Blue Agent coevolution training loops and logs persistence."""
        env = SmartGridRLEnv(max_steps=5, bus_count=9)
        runner = TrainingRunner(env=env, log_dir=self.log_dir)
        
        # Red Agent Setup
        red_config = DQNConfig(batch_size=2)
        red_agent = DQNRedAgent(config=red_config, input_dim=67)
        red_agent.model_manager.base_dir = self.checkpoint_dir
        runner.register_agent("red", red_agent)

        # Blue Agent Setup
        blue_config = DQNConfig(batch_size=2)
        blue_agent = DQNBlueAgent(config=blue_config, input_dim=67)
        blue_agent.model_manager.base_dir = self.checkpoint_dir
        runner.register_agent("blue", blue_agent)

        # Execute training loop for 3 coevolution episodes
        stats = runner.run_training_loop(episodes=3)
        self.assertEqual(stats["episode_count"], 3)
        
        # Verify Red logged metrics
        self.assertIn("red_loss_history", stats)
        self.assertIn("red_epsilon_history", stats)
        self.assertIn("red_attack_success_rate", stats)
        
        # Verify Blue logged metrics
        self.assertIn("blue_loss_history", stats)
        self.assertIn("blue_epsilon_history", stats)
        self.assertIn("blue_detection_success_rate", stats)
        self.assertIn("blue_containment_success_rate", stats)
        self.assertIn("blue_stability_preservation", stats)
        self.assertIn("blue_trust_preservation", stats)
        
        # Confirm training metrics JSON is persisted to disk
        metrics_file = os.path.join(self.log_dir, "training_metrics.json")
        self.assertTrue(os.path.exists(metrics_file))

if __name__ == "__main__":
    unittest.main()
