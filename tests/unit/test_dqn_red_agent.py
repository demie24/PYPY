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
from research.deep_rl.training_runner import TrainingRunner
from research.deep_rl.environment import SmartGridRLEnv

class TestDQNRedAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_dqn_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        # Create temp dirs for checkpoints and logs
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_dqn_network_forward(self):
        """Verifies network layer shapes, activation options, and forward pass output dimensions."""
        input_dim = 67
        output_dim = 54
        
        # Test ReLU
        net = DQNNetwork(input_dim, output_dim, hidden_layers=[32, 16], activation="relu", seed=42)
        x = torch.randn(5, input_dim)
        out = net(x)
        self.assertEqual(out.shape, (5, output_dim))

        # Test Tanh
        net_tanh = DQNNetwork(input_dim, output_dim, hidden_layers=[32], activation="tanh", seed=42)
        out_tanh = net_tanh(x)
        self.assertEqual(out_tanh.shape, (5, output_dim))

    def test_replay_memory_tensors(self):
        """Checks replay memory tensor conversion, batches formatting, and target device casting."""
        memory = DQNReplayMemory(capacity=10, device="cpu")
        
        # Load sample experiences
        for i in range(5):
            state = np.random.randn(67).astype(np.float32)
            next_state = np.random.randn(67).astype(np.float32)
            memory.push(state, 3, 1.0, next_state, False)

        states, actions, rewards, next_states, dones = memory.sample_tensors(batch_size=3)
        
        self.assertEqual(states.shape, (3, 67))
        self.assertEqual(actions.shape, (3, 1))
        self.assertEqual(rewards.shape, (3, 1))
        self.assertEqual(next_states.shape, (3, 67))
        self.assertEqual(dones.shape, (3, 1))
        
        # Datatypes validation
        self.assertEqual(states.dtype, torch.float32)
        self.assertEqual(actions.dtype, torch.int64)
        self.assertEqual(rewards.dtype, torch.float32)
        self.assertEqual(next_states.dtype, torch.float32)
        self.assertEqual(dones.dtype, torch.float32)

    def test_epsilon_greedy_selection(self):
        """Checks epsilon exploration rate decay and action decoding limits."""
        config = DQNConfig(epsilon_start=1.0, epsilon_end=0.1, epsilon_decay=0.9)
        agent = DQNRedAgent(config=config, input_dim=67)
        
        # Verify action space boundaries
        self.assertEqual(agent.action_space_size, 54)

        state = np.random.randn(67).astype(np.float32)
        
        # With epsilon=1.0, selecting actions multiple times should decay epsilon
        action1 = agent.select_action(state, eval_mode=False)
        self.assertLess(agent.epsilon, 1.0)
        self.assertIn("target", action1)
        self.assertIn("attack_type", action1)
        self.assertIn("severity", action1)

        # Force evaluation mode (epsilon shouldn't decay and should choose greedy action)
        current_eps = agent.epsilon
        action_eval = agent.select_action(state, eval_mode=True)
        self.assertEqual(agent.epsilon, current_eps)

    def test_learn_step_execution(self):
        """Ensures backpropagation updates weights and tracks training loss values."""
        config = DQNConfig(batch_size=4, learning_rate=0.01)
        agent = DQNRedAgent(config=config, input_dim=67)
        
        # Populate replay memory
        for _ in range(10):
            state = np.random.randn(67).astype(np.float32)
            next_state = np.random.randn(67).astype(np.float32)
            action_dict = {"target": "Bus_5", "attack_type": "FDIA", "severity": 0.6}
            agent.remember(state, action_dict, 0.5, next_state, False)

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
        
        # Configure model manager target folder inside setUp temp dir
        agent = DQNRedAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir
        
        # Set dummy history/loss metrics
        agent.loss_history = [0.4, 0.2]
        agent.epsilon_history = [0.5, 0.49]
        agent.epsilon = 0.49
        
        # Save model
        chk_path = agent.save_model("test_chk")
        self.assertTrue(os.path.exists(chk_path))

        # Create new agent and reload weights
        new_agent = DQNRedAgent(config=config, input_dim=67)
        new_agent.model_manager.base_dir = self.checkpoint_dir
        new_agent.load_model("test_chk")

        # Assert parity of state dict params
        for p1, p2 in zip(agent.policy_net.parameters(), new_agent.policy_net.parameters()):
            self.assertTrue(torch.equal(p1, p2))
            
        self.assertEqual(new_agent.epsilon, 0.49)
        self.assertEqual(new_agent.loss_history, [0.4, 0.2])

    def test_training_runner_integration(self):
        """Asserts DQN agent integration and training loop output metric persistence."""
        env = SmartGridRLEnv(max_steps=5, bus_count=9)
        runner = TrainingRunner(env=env, log_dir=self.log_dir)
        
        # Override agents model manager directories
        config = DQNConfig(batch_size=2)
        agent = DQNRedAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        runner.register_agent("red", agent)

        # Execute loop for 3 episodes
        stats = runner.run_training_loop(episodes=3)
        self.assertEqual(stats["episode_count"], 3)
        
        # Verify logged metrics
        self.assertIn("red_loss_history", stats)
        self.assertIn("red_epsilon_history", stats)
        self.assertIn("red_attack_success_rate", stats)
        
        # Confirm JSON metrics written to logs dir
        metrics_file = os.path.join(self.log_dir, "training_metrics.json")
        self.assertTrue(os.path.exists(metrics_file))

if __name__ == "__main__":
    unittest.main()
