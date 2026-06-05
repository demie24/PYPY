import os
import sys
import unittest
import numpy as np
import torch
import shutil

# Setup path so we can import research modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl", "ppo")))

from research.deep_rl.ppo.ppo_config import PPOConfig
from research.deep_rl.ppo.actor_network import ActorNetwork
from research.deep_rl.ppo.critic_network import CriticNetwork
from research.deep_rl.ppo.ppo_memory import PPOMemory
from research.deep_rl.ppo.ppo_red_agent import PPORedAgent
from research.deep_rl.training_runner import TrainingRunner
from research.deep_rl.environment import SmartGridRLEnv

class TestPPORedAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_ppo_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        # Create temp dirs for checkpoints and logs
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_actor_network_forward(self):
        """Verifies actor network forward pass probability outputs mapping."""
        input_dim = 67
        output_dim = 54
        net = ActorNetwork(input_dim, output_dim, hidden_layers=[32, 16], activation="relu", seed=42)
        
        x = torch.randn(5, input_dim)
        probs = net(x)
        logits = net.get_logits(x)
        
        self.assertEqual(probs.shape, (5, output_dim))
        self.assertEqual(logits.shape, (5, output_dim))
        # Probabilities sum to 1.0 (approximately)
        for i in range(5):
            self.assertAlmostEqual(probs[i].sum().item(), 1.0, places=5)

    def test_critic_network_forward(self):
        """Verifies critic network value projection mappings."""
        input_dim = 67
        net = CriticNetwork(input_dim, hidden_layers=[32, 16], activation="relu", seed=42)
        
        x = torch.randn(5, input_dim)
        val = net(x)
        self.assertEqual(val.shape, (5, 1))

    def test_ppo_memory_gae(self):
        """Checks PPOMemory trajectory calculation of advantages and returns via GAE."""
        memory = PPOMemory(device="cpu")
        
        # Add 5 dummy steps
        states = [np.random.randn(67).astype(np.float32) for _ in range(5)]
        for i in range(5):
            memory.store(
                state=states[i],
                action=2,
                log_prob=-0.5,
                reward=1.0 if i == 4 else 0.0,
                value=0.5 * i,
                done=True if i == 4 else False
            )
            
        self.assertEqual(len(memory), 5)
        
        advantages, returns = memory.compute_gae(next_value=2.0, gamma=0.99, gae_lambda=0.95)
        
        self.assertEqual(advantages.shape, (5,))
        self.assertEqual(returns.shape, (5,))
        self.assertEqual(advantages.dtype, torch.float32)
        self.assertEqual(returns.dtype, torch.float32)

    def test_ppo_red_agent_action_selection(self):
        """Checks PPO agent action sampling vs deterministic evaluation selection."""
        config = PPOConfig(seed=42)
        agent = PPORedAgent(config=config, input_dim=67)
        state = np.random.randn(67).astype(np.float32)

        # Select action in training mode (sampled)
        action_train = agent.select_action(state, eval_mode=False)
        self.assertIn("target", action_train)
        self.assertIn("attack_type", action_train)
        self.assertIn("severity", action_train)
        self.assertIn("stealth", action_train)
        
        # Verify transition state was cached
        self.assertIsNotNone(agent._last_state)
        self.assertIsNotNone(agent._last_action_idx)
        self.assertIsNotNone(agent._last_log_prob)
        self.assertIsNotNone(agent._last_value)

        # Select action in evaluation mode (argmax)
        agent._last_state = None
        action_eval = agent.select_action(state, eval_mode=True)
        # Should not cache step transition under evaluation mode
        self.assertIsNone(agent._last_state)
        self.assertIn("target", action_eval)

    def test_ppo_red_agent_update_step(self):
        """Ensures PPO update/learning backpropagation updates weights properly."""
        config = PPOConfig(batch_size=4, epochs_per_update=2)
        agent = PPORedAgent(config=config, input_dim=67)

        initial_actor_params = [p.clone() for p in agent.actor.parameters()]
        initial_critic_params = [p.clone() for p in agent.critic.parameters()]

        # Collect trajectory in buffer
        for i in range(5):
            state = np.random.randn(67).astype(np.float32)
            next_state = np.random.randn(67).astype(np.float32)
            action_dict = agent.select_action(state, eval_mode=False)
            agent.remember(state, action_dict, 0.5 if i == 4 else 0.0, next_state, True if i == 4 else False)

        # Run learn step
        agent.learn(None, None, None, np.random.randn(67).astype(np.float32), True)

        # Verify weights were updated
        actor_changed = False
        for p_init, p_new in zip(initial_actor_params, agent.actor.parameters()):
            if not torch.equal(p_init, p_new):
                actor_changed = True
                break
        self.assertTrue(actor_changed)

        critic_changed = False
        for p_init, p_new in zip(initial_critic_params, agent.critic.parameters()):
            if not torch.equal(p_init, p_new):
                critic_changed = True
                break
        self.assertTrue(critic_changed)

        # Verify loss tracking was captured
        self.assertGreater(len(agent.loss_history), 0)
        self.assertGreater(len(agent.actor_loss_history), 0)
        self.assertGreater(len(agent.critic_loss_history), 0)
        self.assertGreater(len(agent.entropy_history), 0)

    def test_checkpoint_save_load(self):
        """Tests checkpoint saving and loading functionality for the PPO agent."""
        config = PPOConfig(seed=42)
        agent = PPORedAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        agent.loss_history = [0.5, 0.3]
        agent.actor_loss_history = [0.2, 0.1]
        agent.critic_loss_history = [0.3, 0.2]
        agent.entropy_history = [0.01, 0.02]

        chk_path = agent.save_model("test_ppo_chk")
        self.assertTrue(os.path.exists(chk_path))

        new_agent = PPORedAgent(config=config, input_dim=67)
        new_agent.model_manager.base_dir = self.checkpoint_dir
        new_agent.load_model("test_ppo_chk")

        for p1, p2 in zip(agent.actor.parameters(), new_agent.actor.parameters()):
            self.assertTrue(torch.equal(p1, p2))
        for p1, p2 in zip(agent.critic.parameters(), new_agent.critic.parameters()):
            self.assertTrue(torch.equal(p1, p2))

        self.assertEqual(new_agent.loss_history, [0.5, 0.3])
        self.assertEqual(new_agent.actor_loss_history, [0.2, 0.1])
        self.assertEqual(new_agent.critic_loss_history, [0.3, 0.2])
        self.assertEqual(new_agent.entropy_history, [0.01, 0.02])

    def test_training_runner_integration(self):
        """Checks PPORedAgent compatibility with the TrainingRunner system."""
        env = SmartGridRLEnv(max_steps=5, bus_count=9)
        runner = TrainingRunner(env=env, log_dir=self.log_dir)

        config = PPOConfig(batch_size=2)
        agent = PPORedAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        runner.register_agent("red", agent)

        # Execute loop for 3 episodes
        stats = runner.run_training_loop(episodes=3)
        self.assertEqual(stats["episode_count"], 3)

        # Verify logged metrics
        self.assertIn("red_loss_history", stats)
        self.assertIn("red_attack_success_rate", stats)

        # Confirm JSON metrics written to logs dir
        metrics_file = os.path.join(self.log_dir, "training_metrics.json")
        self.assertTrue(os.path.exists(metrics_file))

if __name__ == "__main__":
    unittest.main()
