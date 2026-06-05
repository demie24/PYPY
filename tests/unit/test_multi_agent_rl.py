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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl", "ppo")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl", "marl")))

from research.deep_rl.dqn.dqn_red_agent import DQNRedAgent
from research.deep_rl.dqn.dqn_blue_agent import DQNBlueAgent
from research.deep_rl.ppo.ppo_config import PPOConfig
from research.deep_rl.ppo.ppo_red_agent import PPORedAgent
from research.deep_rl.ppo.ppo_blue_agent import PPOBlueAgent

from research.deep_rl.marl.multi_agent_env import MultiAgentGridEnv
from research.deep_rl.marl.agent_registry import AgentRegistry
from research.deep_rl.marl.coordination_manager import CoordinationManager
from research.deep_rl.marl.reward_aggregator import RewardAggregator
from research.deep_rl.marl.marl_runner import MARLRunner

class TestMultiAgentRL(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_marl_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_agent_registration(self):
        """Verifies registry handles DQN and PPO agent registration."""
        registry = AgentRegistry()
        
        # Create dummy configuration/agents
        config = PPOConfig(seed=42)
        ppo_red = PPORedAgent(config=config, input_dim=67)
        dqn_blue = DQNBlueAgent(input_dim=67)
        
        registry.register_agent("ppo_red_1", ppo_red, "red")
        registry.register_agent("dqn_blue_1", dqn_blue, "blue")
        
        self.assertEqual(len(registry.list_agents()), 2)
        self.assertEqual(registry.list_agents("red"), ["ppo_red_1"])
        self.assertEqual(registry.list_agents("blue"), ["dqn_blue_1"])
        
        self.assertIs(registry.get_agent("ppo_red_1"), ppo_red)
        
        # Remove agent
        registry.remove_agent("ppo_red_1")
        self.assertEqual(len(registry.list_agents("red")), 0)

    def test_coordination_resolution(self):
        """Verifies coordination manager handles red/blue conflicts."""
        coordination = CoordinationManager(seed=42)
        
        # Test Red resolution targeting same bus (cooperation)
        red_actions_same = {
            "red_1": {"target": "Bus_5", "severity": 0.4, "stealth": 0.8, "attack_type": "FDIA"},
            "red_2": {"target": "Bus_5", "severity": 0.5, "stealth": 0.6, "attack_type": "FDIA"}
        }
        resolved_red, conflicts = coordination.resolve_red_actions(red_actions_same)
        self.assertEqual(resolved_red["target"], "Bus_5")
        # Severity sums up
        self.assertAlmostEqual(resolved_red["severity"], 0.9)
        # Conflicts is 0
        self.assertEqual(conflicts, 0)
        
        # Test Red resolution targeting different buses (conflict)
        red_actions_diff = {
            "red_1": {"target": "Bus_3", "severity": 0.4, "stealth": 0.8, "attack_type": "FDIA"},
            "red_2": {"target": "Bus_7", "severity": 0.8, "stealth": 0.6, "attack_type": "DoS"}
        }
        resolved_red, conflicts = coordination.resolve_red_actions(red_actions_diff)
        # Highest severity wins
        self.assertEqual(resolved_red["target"], "Bus_7")
        self.assertEqual(resolved_red["severity"], 0.8)
        self.assertEqual(conflicts, 1)

        # Test Blue resolution
        state = np.zeros(67, dtype=np.float32)
        # Put high threat on Bus 3
        # Bus 3 index is 2 * 5 = 10, threat score index is 10 + 3 = 13
        state[13] = 50.0  # Threat score on Bus 3
        
        blue_actions = {
            "blue_1": {"routing_strategy": "ISOLATE_BUS_5", "anomaly_threshold": 0.5},
            "blue_2": {"routing_strategy": "ISOLATE_BUS_3", "anomaly_threshold": 0.5}
        }
        resolved_blue, conflicts = coordination.resolve_blue_actions(blue_actions, state)
        # Should prioritize Bus 3 due to higher threat
        self.assertEqual(resolved_blue["routing_strategy"], "ISOLATE_BUS_3")
        self.assertEqual(conflicts, 1)

    def test_reward_aggregation(self):
        """Verifies INDIVIDUAL, TEAM, and HYBRID aggregation calculations."""
        agg = RewardAggregator(mode="INDIVIDUAL")
        self.assertEqual(agg.aggregate("agent_1", "red", 5.0, 2.0), 5.0)

        agg.set_mode("TEAM")
        self.assertEqual(agg.aggregate("agent_1", "red", 5.0, 2.0), 2.0)

        agg.set_mode("HYBRID", alpha=0.6)
        self.assertAlmostEqual(agg.aggregate("agent_1", "red", 5.0, 2.0), 3.8)

    def test_multi_agent_env_wrapper(self):
        """Checks MultiAgentGridEnv step mechanics and property bindings."""
        env = MultiAgentGridEnv(max_steps=10)
        self.assertEqual(env.state_dim, 67)
        self.assertEqual(env.current_step, 0)
        
        # Test step
        action = {
            "red": {"target": "Bus_5", "severity": 0.5, "attack_type": "FDIA", "stealth": 0.5},
            "blue": {"routing_strategy": "DEFAULT", "anomaly_threshold": 0.5}
        }
        next_state, rewards, done, info = env.step(action)
        self.assertEqual(env.current_step, 1)
        self.assertEqual(len(env.get_encoded_state()), 67)

    def test_marl_runner_execution(self):
        """Verifies MARLRunner registers multiple agents and runs coevolution loops."""
        env = MultiAgentGridEnv(max_steps=5)
        runner = MARLRunner(env=env, log_dir=self.log_dir, reward_mode="HYBRID", reward_alpha=0.5)

        # Setup 2 Red (PPO + DQN) and 2 Blue (PPO + DQN) agents
        ppo_config = PPOConfig(batch_size=2, seed=42)
        
        red_ppo = PPORedAgent(config=ppo_config, input_dim=67)
        red_dqn = DQNRedAgent(input_dim=67)
        blue_ppo = PPOBlueAgent(config=ppo_config, input_dim=67)
        blue_dqn = DQNBlueAgent(input_dim=67)
        
        red_ppo.model_manager.base_dir = self.checkpoint_dir
        blue_ppo.model_manager.base_dir = self.checkpoint_dir
        red_dqn.model_manager.base_dir = self.checkpoint_dir
        blue_dqn.model_manager.base_dir = self.checkpoint_dir

        runner.register_agent("red_ppo", red_ppo, "red")
        runner.register_agent("red_dqn", red_dqn, "red")
        runner.register_agent("blue_ppo", blue_ppo, "blue")
        runner.register_agent("blue_dqn", blue_dqn, "blue")

        # Run 2 episodes training loop
        stats = runner.run_training_loop(episodes=2)
        
        self.assertEqual(stats["episode_count"], 2)
        self.assertEqual(len(stats["coordination_scores"]), 2)
        self.assertEqual(len(stats["conflict_counts"]), 2)
        
        # Verify agent reward tracking
        self.assertIn("red_ppo", stats["agent_rewards_history"])
        self.assertIn("red_dqn", stats["agent_rewards_history"])
        self.assertIn("blue_ppo", stats["agent_rewards_history"])
        self.assertIn("blue_dqn", stats["agent_rewards_history"])

        # Confirm JSON metrics generated
        metrics_file = os.path.join(self.log_dir, "marl_training_metrics.json")
        self.assertTrue(os.path.exists(metrics_file))

if __name__ == "__main__":
    unittest.main()
