import os
import sys
import json
import numpy as np
import random
from typing import Dict, Any, List, Optional

# Ensure parent directories are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "self_play")))

from population_manager import PopulationManager
from fitness_evaluator import FitnessEvaluator
from genetic_operator import GeneticOperator
from elite_selection import EliteSelection
from self_play_runner import SelfPlayRunner

class EvolutionRunner:
    def __init__(
        self,
        population_manager: Optional[PopulationManager] = None,
        fitness_evaluator: Optional[FitnessEvaluator] = None,
        self_play_runner: Optional[SelfPlayRunner] = None,
        log_dir: Optional[str] = None
    ):
        """
        Coordinates population evolution iterations across multiple generations.
        """
        self.manager = population_manager or PopulationManager()
        self.evaluator = fitness_evaluator or FitnessEvaluator()
        self.operator = GeneticOperator(seed=42)
        self.selector = EliteSelection(seed=42)
        self.self_play = self_play_runner or SelfPlayRunner()

        if log_dir is None:
            self.log_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "persistence",
                    "training_logs"
                )
            )
        else:
            self.log_dir = os.path.abspath(log_dir)

        os.makedirs(self.log_dir, exist_ok=True)
        self.generation_stats: List[Dict[str, Any]] = []

    def calculate_diversity(self) -> float:
        """
        Calculates population diversity based on agent learning rate standard deviations.
        """
        lrs = []
        for agent in self.manager.population.values():
            if hasattr(agent, "config") and hasattr(agent.config, "learning_rate"):
                lrs.append(agent.config.learning_rate)
        if len(lrs) < 2:
            return 0.0
        return float(np.std(lrs))

    def evaluate_population_fitness(
        self,
        opponent_team: str,
        eval_episodes: int = 2
    ) -> Dict[str, float]:
        """
        Evaluates the fitness of all agents in the population.
        Runs evaluation games against opponent snapshots to capture win rates, rewards, and stability.
        """
        fitness_scores = {}

        for agent_id, agent in self.manager.population.items():
            wins = 0
            rewards = []
            stability_preservations = []
            success_rates = []

            # Sample opponent snapshot from the self-play pool
            opponents = self.self_play.manager.opponent_pool.list_opponents(team=opponent_team)
            if not opponents:
                # Fallback to instantiating a default baseline opponent
                base_opp_id = f"baseline_{opponent_team}"
                base_opp = self.self_play.instantiate_agent("DQN", opponent_team)
                self.self_play.manager.create_snapshot(base_opp_id, base_opp, opponent_team)
                opponents = self.self_play.manager.opponent_pool.list_opponents(team=opponent_team)

            # Play evaluation episodes
            for _ in range(eval_episodes):
                opp_info = random.choice(opponents)
                opp_instance = self.self_play.instantiate_agent(opp_info["model_type"], opponent_team)
                self.self_play.manager.load_opponent_weights(opp_info["opponent_id"], opp_instance)

                # Run evaluation match
                team_str = self.manager.metadata[agent_id]["team"]
                if team_str == "red":
                    match_res = self.self_play.run_match(
                        red_agent_id=agent_id,
                        red_agent=agent,
                        blue_agent_id=opp_info["opponent_id"],
                        blue_agent=opp_instance,
                        eval_mode=True
                    )
                    outcome = match_res["outcome"]
                else:
                    match_res = self.self_play.run_match(
                        red_agent_id=opp_info["opponent_id"],
                        red_agent=opp_instance,
                        blue_agent_id=agent_id,
                        blue_agent=agent,
                        eval_mode=True
                    )
                    outcome = 1.0 - match_res["outcome"]

                if outcome == 1.0:
                    wins += 1

                # Gather performance metrics
                res = match_res["results"]
                rewards.append(res["agent_rewards"][agent_id])

                # Query agent attributes for success rates and stability
                if hasattr(agent, "get_stability_preservation"):
                    stability_preservations.append(agent.get_stability_preservation())
                else:
                    stability_preservations.append(0.8) # nominal fallback

                if hasattr(agent, "get_attack_success_rate"):
                    success_rates.append(agent.get_attack_success_rate())
                elif hasattr(agent, "get_detection_success_rate"):
                    success_rates.append(agent.get_detection_success_rate())
                else:
                    success_rates.append(0.5)

            # Calculate metrics
            win_rate = wins / max(1, eval_episodes)
            avg_reward = np.mean(rewards)
            stability = np.mean(stability_preservations)
            success = np.mean(success_rates)
            elo = self.self_play.manager.rating_system.get_rating(agent_id)

            fitness_scores[agent_id] = self.evaluator.evaluate({
                "win_rate": win_rate,
                "elo": elo,
                "avg_reward": avg_reward,
                "success_rate": success,
                "stability": stability
            })

        return fitness_scores

    def evolve(
        self,
        generations: int = 2,
        pop_size: int = 4,
        model_type: str = "PPO",
        team: str = "red",
        matchmaking_method: str = "random"
    ) -> List[Dict[str, Any]]:
        """
        Runs the population evolution training lifecycle over multiple generations.
        """
        opponent_team = "blue" if team.lower() == "red" else "red"
        
        # Initialize population
        agent_ids = self.manager.create_population(pop_size, model_type, team)

        # Ensure ELO ratings exist for all agents
        for aid in agent_ids:
            self.self_play.manager.rating_system.get_rating(aid)

        for gen in range(1, generations + 1):
            # 1. Evaluate fitness
            fitness_scores = self.evaluate_population_fitness(opponent_team)

            # Record stats
            fit_vals = list(fitness_scores.values())
            best_fit = max(fit_vals)
            avg_fit = np.mean(fit_vals)
            diversity = self.calculate_diversity()
            
            gen_stat = {
                "generation": gen,
                "best_fitness": best_fit,
                "average_fitness": avg_fit,
                "diversity_score": diversity,
                "fitness_distribution": fitness_scores
            }
            self.generation_stats.append(gen_stat)

            # 2. Select elites to preserve (keep 50% of the population)
            k_elites = max(1, pop_size // 2)
            elites = self.selector.select(fitness_scores, method="top_k", k=k_elites)

            # 3. Repopulate with crossover and mutations
            next_pop = {}
            next_metadata = {}
            
            # Keep elites directly
            for i, elite_id in enumerate(elites):
                elite_agent = self.manager.get_agent(elite_id)
                new_id = f"agent_{team.lower()}_{model_type.lower()}_elite_{i}_gen_{gen}"
                next_pop[new_id] = elite_agent
                next_metadata[new_id] = self.manager.metadata[elite_id]

            # Breed children to fill population size limit
            child_idx = 0
            while len(next_pop) < pop_size:
                parent_a_id = random.choice(elites)
                parent_b_id = random.choice(elites)
                
                parent_a = self.manager.get_agent(parent_a_id)
                parent_b = self.manager.get_agent(parent_b_id)

                child_id = f"agent_{team.lower()}_{model_type.lower()}_child_{child_idx}_gen_{gen}"
                child = self.manager.instantiate_agent(model_type, team)
                
                # Apply crossover
                self.operator.crossover(parent_a, parent_b, child)
                # Apply mutation
                self.operator.mutate(child)

                next_pop[child_id] = child
                next_metadata[child_id] = {
                    "model_type": model_type.upper(),
                    "team": team.lower()
                }
                child_idx += 1

            # Update manager population collections
            self.manager.population = next_pop
            self.manager.metadata = next_metadata

            # 4. Perform self-play training on new population members (1 episode sparring step)
            for aid, agent in self.manager.population.items():
                if "child" in aid:
                    # Train child for 1 episode to optimize parameters
                    self.self_play.run_self_play_training_loop(
                        agent_id=aid,
                        agent_instance=agent,
                        team=team,
                        episodes=1,
                        snapshot_frequency=1,
                        matchmaking_method=matchmaking_method
                    )

            # Save the current generation weights to disk
            self.manager.save_generation(gen)

        # Save metrics JSON to logs directory
        self.save_metrics()
        return self.generation_stats

    def save_metrics(self) -> None:
        """
        Saves generation metrics history to logs directory.
        """
        metrics_file = os.path.join(self.log_dir, "evolution_metrics.json")
        with open(metrics_file, "w") as f:
            json.dump(self.generation_stats, f, indent=4)
