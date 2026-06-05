import os
import json
import time
from typing import Dict, Any, List, Optional
from environment import SmartGridRLEnv
from state_encoder import StateEncoder

class TrainingRunner:
    def __init__(self, env: Optional[SmartGridRLEnv] = None, log_dir: str = None):
        """
        Initializes the training runner to coordinate and log episodic research runs.
        """
        self.env = env or SmartGridRLEnv()
        self.encoder = StateEncoder(self.env.bus_ids, self.env.line_ids)
        
        # Resolve training logs path
        if log_dir is None:
            self.log_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "persistence", "training_logs")
            )
        else:
            self.log_dir = os.path.abspath(log_dir)
            
        os.makedirs(self.log_dir, exist_ok=True)
        self.agents: Dict[str, Any] = {}

    def register_agent(self, agent_id: str, agent: Any):
        """
        Registers a training agent (Red or Blue, tabular or deep networks).
        """
        self.agents[agent_id] = agent

    def run_episode(self) -> Dict[str, Any]:
        """
        Executes a single environment episode, interacting with registered agents.
        Returns a detailed summary of steps, actions, rewards, and performance metrics.
        """
        state = self.env.reset()
        done = False
        
        episode_rewards = {"red": 0.0, "blue": 0.0}
        steps = 0
        history = []

        while not done:
            steps += 1
            # Encode current state for model inputs
            encoded_state = self.encoder.encode(state)
            
            # Select actions from registered agents (fallback to dummy actions if none registered)
            actions = {}
            if "red" in self.agents:
                # Select action (supports select_action interface)
                actions["red"] = self.agents["red"].select_action(encoded_state)
            else:
                actions["red"] = {"target": "Bus_5", "severity": 0.5, "attack_type": "FDIA", "stealth": 0.5}

            if "blue" in self.agents:
                actions["blue"] = self.agents["blue"].select_action(encoded_state)
            else:
                actions["blue"] = {"routing_strategy": "DEFAULT", "rollback_lockout": 0.0, "anomaly_threshold": 0.5}

            # Take step
            next_state, rewards, done, info = self.env.step(actions)
            
            # Accumulate rewards
            episode_rewards["red"] += rewards.get("red", 0.0)
            episode_rewards["blue"] += rewards.get("blue", 0.0)

            # Store transitions for agents if they implement an update/learn method
            encoded_next_state = self.encoder.encode(next_state)
            for agent_id, agent in self.agents.items():
                if hasattr(agent, "remember"):
                    agent.remember(encoded_state, actions.get(agent_id), rewards.get(agent_id, 0.0), encoded_next_state, done)
                if hasattr(agent, "learn"):
                    agent.learn(encoded_state, actions.get(agent_id), rewards.get(agent_id, 0.0), encoded_next_state, done)

            # Record history
            history.append({
                "step": steps,
                "actions": actions,
                "rewards": rewards,
                "done": done
            })
            state = next_state

        return {
            "steps": steps,
            "rewards": episode_rewards,
            "history": history
        }

    def run_training_loop(self, episodes: int = 100) -> Dict[str, Any]:
        """
        Executes a full multi-episode training loop, logging progression statistics.
        """
        start_time = time.time()
        
        stats = {
            "episode_count": 0,
            "rewards_history": {"red": [], "blue": []},
            "best_reward": {"red": -float("inf"), "blue": -float("inf")},
            "average_reward": {"red": 0.0, "blue": 0.0},
            "training_duration_sec": 0.0,
            "convergence_indicator": {"red": 0.0, "blue": 0.0}
        }

        for ep in range(1, episodes + 1):
            ep_res = self.run_episode()
            
            red_r = ep_res["rewards"]["red"]
            blue_r = ep_res["rewards"]["blue"]

            stats["episode_count"] += 1
            stats["rewards_history"]["red"].append(red_r)
            stats["rewards_history"]["blue"].append(blue_r)

            # Update best rewards
            if red_r > stats["best_reward"]["red"]:
                stats["best_reward"]["red"] = red_r
            if blue_r > stats["best_reward"]["blue"]:
                stats["best_reward"]["blue"] = blue_r

        # Calculate average rewards
        stats["average_reward"]["red"] = sum(stats["rewards_history"]["red"]) / episodes
        stats["average_reward"]["blue"] = sum(stats["rewards_history"]["blue"]) / episodes
        
        # Calculate training duration
        stats["training_duration_sec"] = time.time() - start_time

        # Calculate convergence indicators (standard deviation of the last 10% of episodes)
        last_n = max(1, int(episodes * 0.1))
        
        red_last = stats["rewards_history"]["red"][-last_n:]
        blue_last = stats["rewards_history"]["blue"][-last_n:]
        
        red_avg = sum(red_last) / len(red_last)
        blue_avg = sum(blue_last) / len(blue_last)
        
        stats["convergence_indicator"]["red"] = sum((x - red_avg)**2 for x in red_last) / len(red_last)
        stats["convergence_indicator"]["blue"] = sum((x - blue_avg)**2 for x in blue_last) / len(blue_last)

        # Query registered agent metrics if available
        for agent_id, agent in self.agents.items():
            if hasattr(agent, "loss_history"):
                stats[f"{agent_id}_loss_history"] = agent.loss_history
            if hasattr(agent, "epsilon_history"):
                stats[f"{agent_id}_epsilon_history"] = agent.epsilon_history
            if hasattr(agent, "get_attack_success_rate"):
                stats[f"{agent_id}_attack_success_rate"] = agent.get_attack_success_rate()
            if hasattr(agent, "get_detection_success_rate"):
                stats[f"{agent_id}_detection_success_rate"] = agent.get_detection_success_rate()
            if hasattr(agent, "get_containment_success_rate"):
                stats[f"{agent_id}_containment_success_rate"] = agent.get_containment_success_rate()
            if hasattr(agent, "get_stability_preservation"):
                stats[f"{agent_id}_stability_preservation"] = agent.get_stability_preservation()
            if hasattr(agent, "get_trust_preservation"):
                stats[f"{agent_id}_trust_preservation"] = agent.get_trust_preservation()

        # Save metrics to disk
        self.save_metrics(stats)

        return stats

    def save_metrics(self, stats: Dict[str, Any]):
        """
        Saves calculated training statistics to the persistence/training_logs directory.
        """
        metrics_file = os.path.join(self.log_dir, "training_metrics.json")
        with open(metrics_file, "w") as f:
            json.dump(stats, f, indent=4)
