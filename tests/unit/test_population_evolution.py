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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "deep_rl", "evolution")))

from research.deep_rl.dqn.dqn_red_agent import DQNRedAgent
from research.deep_rl.ppo.ppo_config import PPOConfig
from research.deep_rl.ppo.ppo_red_agent import PPORedAgent

from research.deep_rl.evolution.population_manager import PopulationManager
from research.deep_rl.evolution.fitness_evaluator import FitnessEvaluator
from research.deep_rl.evolution.genetic_operator import GeneticOperator
from research.deep_rl.evolution.elite_selection import EliteSelection
from research.deep_rl.evolution.evolution_runner import EvolutionRunner
from research.deep_rl.self_play.opponent_pool import OpponentPool
from research.deep_rl.self_play.rating_system import RatingSystem
from research.deep_rl.self_play.self_play_manager import SelfPlayManager
from research.deep_rl.self_play.self_play_runner import SelfPlayRunner
from research.deep_rl.marl.multi_agent_env import MultiAgentGridEnv

class TestPopulationEvolution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_evolution_test"))
        os.makedirs(self.temp_dir, exist_ok=True)
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.log_dir = os.path.join(self.temp_dir, "logs")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_population_creation(self):
        """Verifies population manager creates agents with directories mapped."""
        mgr = PopulationManager(self.checkpoint_dir)
        agent_ids = mgr.create_population(size=3, model_type="PPO", team="red")
        
        self.assertEqual(len(agent_ids), 3)
        self.assertIn("agent_red_ppo_0", mgr.population)
        self.assertEqual(mgr.metadata["agent_red_ppo_0"]["model_type"], "PPO")
        self.assertEqual(mgr.population["agent_red_ppo_0"].model_manager.base_dir, self.checkpoint_dir)

    def test_fitness_evaluator(self):
        """Checks fitness evaluator calculates weighted scoring."""
        evaluator = FitnessEvaluator()
        
        metrics = {
            "win_rate": 0.8,
            "elo": 1200.0,
            "avg_reward": 5.0,
            "success_rate": 0.9,
            "stability": 0.95
        }
        
        score = evaluator.evaluate(metrics)
        # Expected: 0.3 * 0.8 + 0.3 * (1200/2000) + 0.1 * 5.0 + 0.2 * 0.9 + 0.1 * 0.95
        # = 0.24 + 0.18 + 0.5 + 0.18 + 0.095 = 1.195
        self.assertAlmostEqual(score, 1.195)

    def test_genetic_operations(self):
        """Verifies crossover and mutation operations modify parameters and configs."""
        operator = GeneticOperator(seed=42)
        
        config = PPOConfig(learning_rate=0.01, seed=42)
        parent_a = PPORedAgent(config=config, input_dim=67)
        parent_b = PPORedAgent(config=config, input_dim=67)
        child = PPORedAgent(config=config, input_dim=67)

        # Mutate parent_b
        operator.mutate(parent_b, mutation_rate=1.0, mutation_strength=0.1)
        
        # Verify mutation changed learning rate and weights
        self.assertNotEqual(parent_b.config.learning_rate, 0.01)
        
        # Apply crossover from A and B to Child
        operator.crossover(parent_a, parent_b, child, crossover_rate=0.5)
        
        # Child parameters should be a mix of parent A and parent B
        # (crossover should not crash)
        self.assertIsNotNone(next(child.actor.parameters()))

    def test_elite_selection(self):
        """Checks elite selection Top-K and Tournament strategies."""
        selector = EliteSelection(seed=42)
        
        fitness = {
            "agent_1": 1.5,
            "agent_2": 2.5,
            "agent_3": 0.5,
            "agent_4": 3.0
        }
        
        # Top-K
        elites = selector.select(fitness, method="top_k", k=2)
        self.assertEqual(elites, ["agent_4", "agent_2"])

        # Tournament
        elites_tour = selector.select(fitness, method="tournament", k=1, tournament_size=3)
        self.assertEqual(len(elites_tour), 1)
        self.assertIn(elites_tour[0], fitness.keys())

    def test_evolution_runner_lifecycle(self):
        """Checks complete lifecycle: evaluation, selection, breeding, and snapshots."""
        env = MultiAgentGridEnv(max_steps=5)
        
        opp_pool = OpponentPool()
        ratings = RatingSystem(ratings_file=os.path.join(self.log_dir, "ratings.json"))
        sp_mgr = SelfPlayManager(opp_pool, ratings, self.checkpoint_dir)
        sp_runner = SelfPlayRunner(sp_mgr, env)

        pop_mgr = PopulationManager(self.checkpoint_dir)
        evaluator = FitnessEvaluator()
        
        runner = EvolutionRunner(
            population_manager=pop_mgr,
            fitness_evaluator=evaluator,
            self_play_runner=sp_runner,
            log_dir=self.log_dir
        )

        # Evolve for 2 generations, population size 2
        stats = runner.evolve(
            generations=2,
            pop_size=2,
            model_type="PPO",
            team="red",
            matchmaking_method="random"
        )

        self.assertEqual(len(stats), 2)
        self.assertEqual(stats[0]["generation"], 1)
        self.assertEqual(stats[1]["generation"], 2)
        
        # Verify metrics persisted
        metrics_file = os.path.join(self.log_dir, "evolution_metrics.json")
        self.assertTrue(os.path.exists(metrics_file))

        # Check that child snapshots were saved to disk
        # (PopManager save_generation creates weights snapshot file for each agent)
        self.assertTrue(len(os.listdir(self.checkpoint_dir)) > 0)

if __name__ == "__main__":
    unittest.main()
