import os
import sys
import unittest
import csv
import numpy as np

# Setup paths to import core files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.self_healing.rl.rl_trainer import run_training

class TestRLMaturityTraining(unittest.TestCase):
    def setUp(self):
        # Resolve actual project root (two levels up from tests/integration/)
        self.project_root = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
        self.checkpoints_dir = os.path.join(self.project_root, "checkpoints")
        self.logs_dir = os.path.join(self.project_root, "training_logs")
        self.analytics_dir = os.path.join(self.project_root, "analytics")

    def test_run_training_ppo_integration(self):
        """
        Runs PPO training for 5 episodes to verify integration of curriculum learning,
        stabilization protections, analytics CSV logging, and checkpoint saving.
        """
        # Run 5 episodes of PPO training
        run_training(agent_type="PPO", num_episodes=5, max_steps=5, checkpoint_interval=2)
        
        # 1. Verify directories were created
        self.assertTrue(os.path.exists(self.checkpoints_dir))
        self.assertTrue(os.path.exists(self.logs_dir))
        self.assertTrue(os.path.exists(self.analytics_dir))
        
        # 2. Verify analytics CSV contains data and correct headers
        csv_path = os.path.join(self.analytics_dir, "rl_training_analytics.csv")
        self.assertTrue(os.path.exists(csv_path))
        
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
            # Verify columns
            self.assertEqual(headers[0], "episode")
            self.assertEqual(headers[1], "curriculum_level")
            self.assertEqual(headers[4], "reward")
            self.assertEqual(headers[7], "success_rate")
            self.assertEqual(headers[8], "blocked_action_frequency")
            self.assertEqual(headers[9], "rollback_count")
            self.assertEqual(headers[10], "containment_conflicts")
            
            # Read first row
            first_row = next(reader)
            self.assertEqual(len(first_row), 21)
            self.assertEqual(first_row[0], "1") # Episode 1
            
        # 3. Verify logging was generated
        log_path = os.path.join(self.logs_dir, "rl_training_run.log")
        self.assertTrue(os.path.exists(log_path))
        self.assertTrue(os.path.getsize(log_path) > 0)
        
        # 4. Verify checkpoints were generated
        final_checkpoint = os.path.join(self.checkpoints_dir, "ppo_self_healing.pt")
        self.assertTrue(os.path.exists(final_checkpoint))
        
        # Verify interval checkpoints
        interval_checkpoint_1 = os.path.join(self.checkpoints_dir, "ppo_self_healing_ep_2.pt")
        interval_checkpoint_2 = os.path.join(self.checkpoints_dir, "ppo_self_healing_ep_4.pt")
        self.assertTrue(os.path.exists(interval_checkpoint_1))
        self.assertTrue(os.path.exists(interval_checkpoint_2))

    def test_run_training_dqn_integration(self):
        """
        Runs DQN training for 5 episodes to verify Double-DQN capability.
        """
        run_training(agent_type="DQN", num_episodes=5, max_steps=5, checkpoint_interval=2)
        
        # Verify DQN final checkpoint exists
        final_checkpoint = os.path.join(self.checkpoints_dir, "dqn_self_healing.pt")
        self.assertTrue(os.path.exists(final_checkpoint))

if __name__ == "__main__":
    unittest.main()
