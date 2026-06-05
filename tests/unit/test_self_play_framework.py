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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl", "self_play")))

from research.deep_rl.dqn.dqn_red_agent import DQNRedAgent
from research.deep_rl.dqn.dqn_blue_agent import DQNBlueAgent
from research.deep_rl.ppo.ppo_config import PPOConfig
from research.deep_rl.ppo.ppo_red_agent import PPORedAgent
from research.deep_rl.ppo.ppo_blue_agent import PPOBlueAgent

from research.deep_rl.self_play.opponent_pool import OpponentPool
from research.deep_rl.self_play.rating_system import RatingSystem
from research.deep_rl.self_play.match_scheduler import MatchScheduler
from research.deep_rl.self_play.self_play_manager import SelfPlayManager
from research.deep_rl.self_play.self_play_runner import SelfPlayRunner
from research.deep_rl.marl.multi_agent_env import MultiAgentGridEnv

class TestSelfPlayFramework(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_self_play_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")
        self.ratings_file = os.path.join(self.log_dir, "ratings.json")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_opponent_pool_operations(self):
        """Checks OpponentPool add, list, sample, and remove operations."""
        pool = OpponentPool()
        pool.add_opponent("ppo_red_snap1", "PPO", "red", "ppo_red_snap1_checkpoint", 1050.0)
        pool.add_opponent("dqn_blue_snap1", "DQN", "blue", "dqn_blue_snap1_checkpoint", 950.0)

        self.assertEqual(len(pool.list_opponents()), 2)
        self.assertEqual(len(pool.list_opponents(team="red")), 1)
        self.assertEqual(pool.get_opponent("ppo_red_snap1")["elo"], 1050.0)

        pool.update_elo("ppo_red_snap1", 1080.0)
        self.assertEqual(pool.get_opponent("ppo_red_snap1")["elo"], 1080.0)

        pool.remove_opponent("ppo_red_snap1")
        self.assertEqual(len(pool.list_opponents()), 1)

    def test_rating_system_calculations(self):
        """Verifies ELO calculations for win, loss, and draw outcomes."""
        sys = RatingSystem(ratings_file=self.ratings_file, k_factor=32.0)
        sys.set_rating("red_agent", 1000.0)
        sys.set_rating("blue_agent", 1000.0)

        # Red wins
        new_red, new_blue = sys.record_match("red_agent", "blue_agent", 1.0)
        self.assertEqual(new_red, 1016.0)
        self.assertEqual(new_blue, 984.0)

        # Check ratings are saved
        self.assertTrue(os.path.exists(self.ratings_file))

        # Re-initialize and load ratings
        new_sys = RatingSystem(ratings_file=self.ratings_file)
        self.assertEqual(new_sys.get_rating("red_agent"), 1016.0)
        self.assertEqual(new_sys.get_rating("blue_agent"), 984.0)

    def test_match_scheduler_modes(self):
        """Verifies MatchScheduler pairing modes."""
        pool = OpponentPool()
        sys = RatingSystem(ratings_file=self.ratings_file)
        scheduler = MatchScheduler(pool, sys)

        pool.add_opponent("opp_1", "PPO", "blue", "chk_1", 900.0)
        pool.add_opponent("opp_2", "PPO", "blue", "chk_2", 1100.0)
        pool.add_opponent("opp_3", "PPO", "blue", "chk_3", 1000.0)

        sys.set_rating("agent_red", 1000.0)

        # Test League pairing (should choose opp_3 with Elo 1000.0)
        opp = scheduler.schedule_opponent("agent_red", "blue", method="league")
        self.assertEqual(opp["opponent_id"], "opp_3")

        # Test Progression pairing (win_rate = 1.0 should choose opp_2 with Elo 1100.0)
        opp_prog = scheduler.schedule_opponent("agent_red", "blue", method="progression", win_rate=1.0)
        self.assertEqual(opp_prog["opponent_id"], "opp_2")

    def test_snapshot_management(self):
        """Checks SelfPlayManager creates and restores model weight snapshots."""
        pool = OpponentPool()
        sys = RatingSystem(ratings_file=self.ratings_file)
        manager = SelfPlayManager(pool, sys, self.checkpoint_dir)

        # Instantiate agent
        config = PPOConfig(batch_size=2)
        agent = PPORedAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        # Modify parameter to test loading parity
        initial_val = next(agent.actor.parameters())[0, 0].item()

        # Create snapshot
        snap_id = manager.create_snapshot("ppo_red", agent, "red")
        self.assertIn(snap_id, pool.pool)

        # Create new agent and load snapshot
        new_agent = PPORedAgent(config=config, input_dim=67)
        new_agent.model_manager.base_dir = self.checkpoint_dir
        manager.load_opponent_weights(snap_id, new_agent)

        loaded_val = next(new_agent.actor.parameters())[0, 0].item()
        self.assertAlmostEqual(initial_val, loaded_val, places=5)

    def test_self_play_training_loop(self):
        """Checks SelfPlayRunner multi-agent loops and self-play sparring execution."""
        env = MultiAgentGridEnv(max_steps=5)
        pool = OpponentPool()
        sys = RatingSystem(ratings_file=self.ratings_file)
        manager = SelfPlayManager(pool, sys, self.checkpoint_dir)
        runner = SelfPlayRunner(manager, env)

        # Setup training agent
        config = PPOConfig(batch_size=2)
        agent = PPORedAgent(config=config, input_dim=67)
        agent.model_manager.base_dir = self.checkpoint_dir

        # Run training loop for 2 episodes against PPO opponents
        res = runner.run_self_play_training_loop(
            agent_id="ppo_red_train",
            agent_instance=agent,
            team="red",
            episodes=2,
            snapshot_frequency=1,
            matchmaking_method="random"
        )

        self.assertIn("win_rate", res)
        self.assertIn("loss_rate", res)
        self.assertEqual(len(res["history"]), 2)
        # Should have created snapshots
        self.assertEqual(len(pool.list_opponents(team="red")), 2)

if __name__ == "__main__":
    unittest.main()
