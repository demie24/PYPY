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
from research.deep_rl.ppo.ppo_blue_agent import PPOBlueAgent
from research.deep_rl.training_runner import TrainingRunner
from research.deep_rl.environment import SmartGridRLEnv

class TestPPOBlueAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_ppo_blue_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_actor_network_forward_blue(self):
        """Verifies blue actor network forward pass probability outputs shape (32)."""
        input_dim = 67
        output_dim = 32
        net = ActorNetwork(input_dim, output_dim, hidden_layers=[32], activation="relu", seed=42)
        
        x = torch.randn(3, input_dim)
        probs = net(x)
        self.assertEqual(probs.shape, (3, output_dim))
        for i in range(3):
            self.assertAlmostEqual(probs[i].sum().item(), 1.0, places=5)

    def test_critic_network_forward_blue(self):
        """Verifies critic network mapping for Blue Agent state utility."""
        input_dim = 67
        net = CriticNetwork(input_dim, hidden_layers=[32], activation="relu", seed=42)
        x = torch.randn(3, input_dim)
        self.assertEqual(net(x).shape, (3, 1))

    def test_ppo_blue_agent_action_selection(self):
        """Checks Blue agent action sampling vs evaluation choices."""
        config = PPOConfig(seed=42)
        agent = PPOBlueAgent(config=config, input_dim=67)
        state = np.random.randn(67).astype(np.float32)

        # Training action selection (samples)
        action_train = agent.select_action(state, eval_mode=False)
        self.assertIn("routing_strategy", action_train)
        self.assertIn("anomaly_threshold", action_train)
        self.assertIn("rollback_lockout", action_train)
        self.assertIn("trust_decay_speed", action_train)
        
        # Verify cached transition step
        self.assertIsNotNone(agent._last_state)
        self.assertIsNotNone(agent._last_action_idx)
        self.assertIsNotNone(agent._last_log_prob)
        self.assertIsNotNone(agent._last_value)

        # Evaluation action selection (argmax)
        agent._last_state = None
        action_eval = agent.select_action(state, eval_mode=True)
        self.assertIsNone(agent._last_state)
        self.assertIn("routing_strategy", action_eval)

    def test_ppo_blue_agent_update_step(self):
        """Ensures PPO Blue agent parameter updates happen during learning updates."""
        config = PPOConfig(batch_size=4, epochs_per_update=2)
        agent = PPOBlueAgent(config=config, input_dim=67)

        initial_actor_params = [p.clone() for p in agent.actor.parameters()]
        initial_critic_params = [p.clone() for p in agent.critic.parameters()]

        # Collect transitions to trigger a learning step
        for i in range(5):
            state = np.random.randn(67).astype(np.float32)
            next_state = np.random.randn(67).astype(np.float32)
            action_dict = agent.select_action(state, eval_mode=False)
            agent.remember(state, action_dict, 0.5, next_state, True if i == 4 else False)

        # Execute learn
        agent.learn(None, None, None, np.random.randn(67).astype(np.float32), True)

        # Confirm parameter update convergence
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

        self.assertGreater(len(agent.loss_history), 0)

    def test_checkpoint_save_load_blue(self):
        """Tests saving and loading checkpoints for PPO Blue agent."""
        config = PPOConfig(seed=42)
        agent = PPOBlueAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        agent.loss_history = [0.1]
        agent.total_steps = 100
        agent.false_positive_count = 5
        agent.total_clean_steps = 50

        chk_path = agent.save_model("test_ppo_blue_chk")
        self.assertTrue(os.path.exists(chk_path))

        new_agent = PPOBlueAgent(config=config, input_dim=67)
        new_agent.model_manager.base_dir = self.checkpoint_dir
        new_agent.load_model("test_ppo_blue_chk")

        for p1, p2 in zip(agent.actor.parameters(), new_agent.actor.parameters()):
            self.assertTrue(torch.equal(p1, p2))
        for p1, p2 in zip(agent.critic.parameters(), new_agent.critic.parameters()):
            self.assertTrue(torch.equal(p1, p2))

        self.assertEqual(new_agent.loss_history, [0.1])
        self.assertEqual(new_agent.total_steps, 100)
        self.assertEqual(new_agent.get_false_positive_rate(), 0.1)

    def test_training_runner_integration_blue(self):
        """Verifies TrainingRunner registers PPO Blue agent successfully."""
        env = SmartGridRLEnv(max_steps=5, bus_count=9)
        runner = TrainingRunner(env=env, log_dir=self.log_dir)

        config = PPOConfig(batch_size=2)
        agent = PPOBlueAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        runner.register_agent("blue", agent)

        stats = runner.run_training_loop(episodes=3)
        self.assertEqual(stats["episode_count"], 3)
        self.assertIn("blue_loss_history", stats)
        self.assertIn("blue_detection_success_rate", stats)
        self.assertIn("blue_containment_success_rate", stats)

    def test_ppo_red_vs_ppo_blue_arena(self):
        """Coevolution training check comparing both PPO Red and PPO Blue agents."""
        env = SmartGridRLEnv(max_steps=5, bus_count=9)
        runner = TrainingRunner(env=env, log_dir=self.log_dir)

        config_red = PPOConfig(batch_size=2, seed=12)
        config_blue = PPOConfig(batch_size=2, seed=34)

        agent_red = PPORedAgent(config=config_red, input_dim=67)
        agent_blue = PPOBlueAgent(config=config_blue, input_dim=67)
        agent_red.model_manager.base_dir = self.checkpoint_dir
        agent_blue.model_manager.base_dir = self.checkpoint_dir

        runner.register_agent("red", agent_red)
        runner.register_agent("blue", agent_blue)

        stats = runner.run_training_loop(episodes=3)
        self.assertEqual(stats["episode_count"], 3)
        self.assertIn("red_loss_history", stats)
        self.assertIn("blue_loss_history", stats)

if __name__ == "__main__":
    unittest.main()
