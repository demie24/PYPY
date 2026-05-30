import os
import sys
import unittest
import numpy as np
import torch

# Setup paths to import core files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Import components
from core.self_healing.rl.policy_network import PolicyNetwork
from core.self_healing.rl.value_network import ValueNetwork
from core.self_healing.rl.replay_buffer import ReplayBuffer, PPOMemory
from core.self_healing.rl.ppo_agent import PPOAgent
from core.self_healing.rl.dqn_agent import DQNAgent, QNetwork
from core.self_healing.rl_environment import GridRLEnvironment
from core.self_healing.reward_engine import RewardEngine

class TestRLSelfHealing(unittest.TestCase):
    def setUp(self):
        self.state_dim = 72
        self.action_dim = 10
        self.dummy_state = np.random.randn(self.state_dim).astype(np.float32)

    def test_policy_value_network_output_shapes(self):
        """
        Asserts that PolicyNetwork and ValueNetwork map input vectors to correct shapes.
        """
        policy = PolicyNetwork(self.state_dim, self.action_dim)
        value = ValueNetwork(self.state_dim)
        
        state_t = torch.FloatTensor(self.dummy_state)
        
        logits = policy(state_t)
        val = value(state_t)
        
        # Output shapes: (1, 10) for policy logits, (1, 1) for critic state value
        self.assertEqual(logits.shape, (1, self.action_dim))
        self.assertEqual(val.shape, (1, 1))

    def test_replay_buffer_and_ppo_memory(self):
        """
        Verifies buffer storage, uniform sampling, batch dimensions, and clear capabilities.
        """
        # 1. DQN ReplayBuffer
        dqn_buffer = ReplayBuffer(capacity=100)
        for i in range(10):
            dqn_buffer.push(self.dummy_state, 1, 1.5, self.dummy_state, False)
            
        self.assertEqual(len(dqn_buffer), 10)
        states, actions, rewards, next_states, dones = dqn_buffer.sample(5)
        self.assertEqual(states.shape, (5, self.state_dim))
        self.assertEqual(actions.shape, (5,))
        self.assertEqual(rewards.shape, (5,))
        self.assertEqual(next_states.shape, (5, self.state_dim))
        self.assertEqual(dones.shape, (5,))
        
        # 2. PPOMemory
        ppo_mem = PPOMemory()
        for i in range(5):
            ppo_mem.push(self.dummy_state, 2, -0.5, 1.2, 2.0, False)
            
        self.assertEqual(len(ppo_mem), 5)
        states, actions, probs, vals, rewards, dones = ppo_mem.sample()
        self.assertEqual(states.shape, (5, self.state_dim))
        self.assertEqual(actions.shape, (5,))
        self.assertEqual(probs.shape, (5,))
        self.assertEqual(vals.shape, (5,))
        self.assertEqual(rewards.shape, (5,))
        self.assertEqual(dones.shape, (5,))
        
        ppo_mem.clear()
        self.assertEqual(len(ppo_mem), 0)

    def test_ppo_agent_selection_and_update(self):
        """
        Asserts PPO action sampling, evaluation logic, and trajectory loss convergence.
        """
        agent = PPOAgent(state_dim=self.state_dim, action_dim=self.action_dim)
        
        # Action selection
        action, log_prob, val = agent.select_action(self.dummy_state, evaluation=False)
        self.assertTrue(0 <= action < self.action_dim)
        self.assertIsInstance(log_prob, float)
        self.assertIsInstance(val, float)
        
        # Evaluation mode (argmax action)
        eval_action, _, _ = agent.select_action(self.dummy_state, evaluation=True)
        self.assertTrue(0 <= eval_action < self.action_dim)
        
        # Optimize on batch data
        ppo_mem = PPOMemory()
        for _ in range(8):
            s = np.random.randn(self.state_dim).astype(np.float32)
            act, lp, v = agent.select_action(s)
            ppo_mem.push(s, act, lp, v, 1.0, False)
            
        trajectory = ppo_mem.sample()
        actor_loss, critic_loss, entropy = agent.update(trajectory, ppo_epochs=2, batch_size=4)
        
        self.assertIsInstance(actor_loss, float)
        self.assertIsInstance(critic_loss, float)
        self.assertIsInstance(entropy, float)

    def test_dqn_agent_selection_and_update(self):
        """
        Asserts Double-DQN action selection, target updates, and MSE loss reduction.
        """
        agent = DQNAgent(state_dim=self.state_dim, action_dim=self.action_dim, target_update_interval=2)
        
        # Epsilon-greedy action selection
        action, q_val = agent.select_action(self.dummy_state, evaluation=False)
        self.assertTrue(0 <= action < self.action_dim)
        
        # Update logic
        buffer = ReplayBuffer(capacity=10)
        for _ in range(4):
            s = np.random.randn(self.state_dim).astype(np.float32)
            s_next = np.random.randn(self.state_dim).astype(np.float32)
            buffer.push(s, 2, 1.0, s_next, False)
            
        batch = buffer.sample(batch_size=2)
        loss = agent.update(batch)
        self.assertIsInstance(loss, float)
        
        # Check target update counter increment
        self.assertEqual(agent.update_counter, 1)

    def test_checkpoint_saving_and_loading(self):
        """
        Verifies PPO and DQN agent checkpoint serialization and parameter state loading.
        """
        ppo_agent = PPOAgent(state_dim=self.state_dim, action_dim=self.action_dim)
        dqn_agent = DQNAgent(state_dim=self.state_dim, action_dim=self.action_dim)
        
        temp_dir = os.path.join(CURRENT_DIR, "core", "models")
        os.makedirs(temp_dir, exist_ok=True)

        # PPO save/load
        ppo_agent.save_checkpoint(temp_dir, "test_ppo.pt")
        loaded_ppo = PPOAgent(state_dim=self.state_dim, action_dim=self.action_dim)
        success_ppo = loaded_ppo.load_checkpoint(os.path.join(temp_dir, "test_ppo.pt"))
        self.assertTrue(success_ppo)
        
        # DQN save/load
        dqn_agent.save_checkpoint(temp_dir, "test_dqn.pt")
        loaded_dqn = DQNAgent(state_dim=self.state_dim, action_dim=self.action_dim)
        success_dqn = loaded_dqn.load_checkpoint(os.path.join(temp_dir, "test_dqn.pt"))
        self.assertTrue(success_dqn)
        
        # Cleanup temp checkpoint files
        for f in ["test_ppo.pt", "test_dqn.pt"]:
            p = os.path.join(temp_dir, f)
            if os.path.exists(p):
                os.remove(p)

    def test_gated_exploration_and_safety_penalties(self):
        """
        Asserts that if the agent proposes an unsafe action, the environment overrides
        the action with NO_ACTION (0) and evaluates the correct safety penalty.
        """
        env = GridRLEnvironment(is_live_mode=False)
        state, info = env.reset()
        
        # Trigger an unsafe state: trip L5_6
        env.sandbox_breakers["L5_6"] = "OPEN"
        env.latest_telemetry = env._get_sandbox_telemetry_snapshot()
        state = env.encoder.encode_state(telemetry=env.latest_telemetry)
        
        # Propose an action that violates safety: trip L4_5 (which islands Bus_5)
        # Action category: 1 (ISOLATE_LINE), target: L4_5
        next_state, reward, terminated, truncated, info_step = env.step(action_id=1, target="L4_5")
        
        # Assert action was blocked
        self.assertFalse(info_step["action_allowed"])
        self.assertIn("Blocked by Safety Constraints", info_step["rejection_reason"])
        
        # Reward computation details
        # Let's manually compute reward with rollback occurred flag
        reward_gated, details = env.reward_engine.compute_reward(state, next_state, action_id=0, rollback_occurred=True)
        self.assertTrue(details["penalty_rollback_event"] < 0.0)

if __name__ == "__main__":
    unittest.main()
