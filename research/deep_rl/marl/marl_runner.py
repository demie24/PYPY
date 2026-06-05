import os
import json
import time
import numpy as np
from typing import Dict, Any, List, Optional

from multi_agent_env import MultiAgentGridEnv
from agent_registry import AgentRegistry
from coordination_manager import CoordinationManager
from reward_aggregator import RewardAggregator

class MARLRunner:
    def __init__(
        self,
        env: Optional[MultiAgentGridEnv] = None,
        log_dir: Optional[str] = None,
        reward_mode: str = "INDIVIDUAL",
        reward_alpha: float = 0.5
    ):
        """
        Coordinates multi-agent training loops and logs episodic performance metrics.
        """
        self.env = env or MultiAgentGridEnv()
        self.registry = AgentRegistry()
        self.coordination = CoordinationManager(seed=42)
        self.aggregator = RewardAggregator(mode=reward_mode, alpha=reward_alpha)

        # Resolve logs directory
        if log_dir is None:
            self.log_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "persistence", "training_logs")
            )
        else:
            self.log_dir = os.path.abspath(log_dir)

        os.makedirs(self.log_dir, exist_ok=True)

    def register_agent(self, agent_id: str, agent_instance: Any, team: str) -> None:
        """
        Registers a training agent to the runner's registry.
        """
        self.registry.register_agent(agent_id, agent_instance, team)

    def run_episode(self, eval_mode: bool = False) -> Dict[str, Any]:
        """
        Runs a single multi-agent episode. Resolves action conflicts, distributes rewards,
        and triggers learning updates.
        """
        self.env.reset()
        done = False
        
        red_agent_ids = self.registry.list_agents("red")
        blue_agent_ids = self.registry.list_agents("blue")
        
        # Initialize episode logs
        agent_rewards = {aid: 0.0 for aid in red_agent_ids + blue_agent_ids}
        team_rewards = {"red": 0.0, "blue": 0.0}
        
        steps = 0
        total_conflicts = 0
        total_actions = 0
        history = []

        while not done:
            steps += 1
            state_vec = self.env.get_encoded_state()

            # 1. Collect agent actions
            red_actions = {}
            for aid in red_agent_ids:
                agent = self.registry.get_agent(aid)
                # Select action (supports both DQN and PPO select_action interface)
                red_actions[aid] = agent.select_action(state_vec, eval_mode=eval_mode)
                total_actions += 1

            blue_actions = {}
            for aid in blue_agent_ids:
                agent = self.registry.get_agent(aid)
                blue_actions[aid] = agent.select_action(state_vec, eval_mode=eval_mode)
                total_actions += 1

            # 2. Resolve conflicts and compile coordinated actions
            resolved_red, red_conflicts = self.coordination.resolve_red_actions(red_actions)
            resolved_blue, blue_conflicts = self.coordination.resolve_blue_actions(blue_actions, state_vec)
            
            step_conflicts = red_conflicts + blue_conflicts
            total_conflicts += step_conflicts

            # 3. Take simulation step
            next_state, env_rewards, done, info = self.env.step({
                "red": resolved_red,
                "blue": resolved_blue
            })
            next_state_vec = self.env.get_encoded_state()

            # Accumulate coordinated team rewards
            team_rewards["red"] += env_rewards.get("red", 0.0)
            team_rewards["blue"] += env_rewards.get("blue", 0.0)

            # 4. Aggregated Rewards calculation & transition storage
            # Calculate rewards for Red agents
            for aid in red_agent_ids:
                agent = self.registry.get_agent(aid)
                agent_action = red_actions[aid]
                
                # Individual reward for the agent's action
                ind_reward = self.env.env.get_reward("red", agent_action, next_state)
                # Coordinated team reward
                t_reward = env_rewards.get("red", 0.0)
                
                agg_reward = self.aggregator.aggregate(aid, "red", ind_reward, t_reward)
                agent_rewards[aid] += agg_reward

                if not eval_mode:
                    if hasattr(agent, "remember"):
                        agent.remember(state_vec, agent_action, agg_reward, next_state_vec, done)
                    if hasattr(agent, "learn"):
                        agent.learn(state_vec, agent_action, agg_reward, next_state_vec, done)

            # Calculate rewards for Blue agents
            for aid in blue_agent_ids:
                agent = self.registry.get_agent(aid)
                agent_action = blue_actions[aid]
                
                ind_reward = self.env.env.get_reward("blue", agent_action, next_state)
                t_reward = env_rewards.get("blue", 0.0)
                
                agg_reward = self.aggregator.aggregate(aid, "blue", ind_reward, t_reward)
                agent_rewards[aid] += agg_reward

                if not eval_mode:
                    if hasattr(agent, "remember"):
                        agent.remember(state_vec, agent_action, agg_reward, next_state_vec, done)
                    if hasattr(agent, "learn"):
                        agent.learn(state_vec, agent_action, agg_reward, next_state_vec, done)

            # Step logging
            history.append({
                "step": steps,
                "conflicts": step_conflicts,
                "env_rewards": env_rewards
            })

        # Calculate coordination efficiency
        coordination_score = 1.0 if total_actions == 0 else (total_actions - total_conflicts) / max(1, total_actions)

        return {
            "steps": steps,
            "agent_rewards": agent_rewards,
            "team_rewards": team_rewards,
            "conflicts": total_conflicts,
            "coordination_score": max(0.0, min(1.0, coordination_score)),
            "history": history
        }

    def run_training_loop(self, episodes: int = 100) -> Dict[str, Any]:
        """
        Runs a multi-agent training loop over a set number of episodes, logging progress metrics.
        """
        start_time = time.time()
        
        red_agent_ids = self.registry.list_agents("red")
        blue_agent_ids = self.registry.list_agents("blue")
        all_agent_ids = red_agent_ids + blue_agent_ids

        stats = {
            "episode_count": 0,
            "team_rewards_history": {"red": [], "blue": []},
            "agent_rewards_history": {aid: [] for aid in all_agent_ids},
            "coordination_scores": [],
            "conflict_counts": [],
            "training_duration_sec": 0.0,
            "agent_metrics": {}
        }

        for ep in range(1, episodes + 1):
            ep_res = self.run_episode(eval_mode=False)
            
            stats["episode_count"] += 1
            stats["team_rewards_history"]["red"].append(ep_res["team_rewards"]["red"])
            stats["team_rewards_history"]["blue"].append(ep_res["team_rewards"]["blue"])
            stats["coordination_scores"].append(ep_res["coordination_score"])
            stats["conflict_counts"].append(ep_res["conflicts"])

            for aid in all_agent_ids:
                stats["agent_rewards_history"][aid].append(ep_res["agent_rewards"][aid])

        stats["training_duration_sec"] = time.time() - start_time

        # Extract agent internal metrics (loss/entropy/etc.)
        for aid in all_agent_ids:
            agent = self.registry.get_agent(aid)
            agent_metrics = {}
            if hasattr(agent, "loss_history") and agent.loss_history:
                agent_metrics["loss"] = agent.loss_history
            if hasattr(agent, "entropy_history") and agent.entropy_history:
                agent_metrics["entropy"] = agent.entropy_history
            if hasattr(agent, "get_attack_success_rate"):
                agent_metrics["attack_success_rate"] = agent.get_attack_success_rate()
            if hasattr(agent, "get_detection_success_rate"):
                agent_metrics["detection_success_rate"] = agent.get_detection_success_rate()
            if hasattr(agent, "get_containment_success_rate"):
                agent_metrics["containment_success_rate"] = agent.get_containment_success_rate()
            if hasattr(agent, "get_false_positive_rate"):
                agent_metrics["false_positive_rate"] = agent.get_false_positive_rate()

            stats["agent_metrics"][aid] = agent_metrics

        # Save metrics to logs dir
        self.save_metrics(stats)

        return stats

    def save_metrics(self, stats: Dict[str, Any]) -> None:
        """
        Saves calculated metrics to persistence training logs.
        """
        metrics_file = os.path.join(self.log_dir, "marl_training_metrics.json")
        with open(metrics_file, "w") as f:
            json.dump(stats, f, indent=4)
