import os
import sys
import numpy as np
from typing import Dict, Any, List, Optional

# Ensure parent directories are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "marl")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dqn")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ppo")))

from dqn_red_agent import DQNRedAgent
from dqn_blue_agent import DQNBlueAgent
from ppo_config import PPOConfig
from ppo_red_agent import PPORedAgent
from ppo_blue_agent import PPOBlueAgent

from multi_agent_env import MultiAgentGridEnv
from marl_runner import MARLRunner
from self_play_manager import SelfPlayManager
from match_scheduler import MatchScheduler

class SelfPlayRunner:
    def __init__(
        self,
        manager: Optional[SelfPlayManager] = None,
        env: Optional[MultiAgentGridEnv] = None
    ):
        """
        Coordinates execution of training and evaluation matches under the self-play framework.
        """
        self.manager = manager or SelfPlayManager()
        self.env = env or MultiAgentGridEnv()
        self.scheduler = MatchScheduler(self.manager.opponent_pool, self.manager.rating_system)

    def instantiate_agent(self, model_type: str, team: str) -> Any:
        """
        Dynamically instantiates an agent model instance.
        """
        t_lower = team.lower()
        m_upper = model_type.upper()

        if m_upper == "DQN":
            if t_lower == "red":
                agent = DQNRedAgent()
            else:
                agent = DQNBlueAgent()
        elif m_upper == "PPO":
            config = PPOConfig(batch_size=2, seed=42)
            if t_lower == "red":
                agent = PPORedAgent(config=config)
            else:
                agent = PPOBlueAgent(config=config)
        else:
            raise ValueError(f"Unknown agent model type: {model_type}")

        agent.model_manager.base_dir = self.manager.model_manager.base_dir
        return agent

    def run_match(
        self,
        red_agent_id: str,
        red_agent: Any,
        blue_agent_id: str,
        blue_agent: Any,
        eval_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a sparring match between Red and Blue agents. Returns outcomes and ELO updates.
        """
        runner = MARLRunner(env=self.env, log_dir=self.manager.model_manager.base_dir)
        runner.register_agent(red_agent_id, red_agent, "red")
        runner.register_agent(blue_agent_id, blue_agent, "blue")

        # Run episode
        results = runner.run_episode(eval_mode=eval_mode)

        red_reward = results["team_rewards"]["red"]
        blue_reward = results["team_rewards"]["blue"]

        # Determine outcome for Red agent (outcome = 1.0 (win), 0.0 (loss), 0.5 (draw))
        if red_reward > blue_reward + 0.1:
            outcome = 1.0
        elif blue_reward > red_reward + 0.1:
            outcome = 0.0
        else:
            outcome = 0.5

        # Update Elo ratings
        new_red_elo, new_blue_elo = self.manager.rating_system.record_match(
            red_agent_id,
            blue_agent_id,
            outcome
        )

        # Update Elo inside opponent pool if they are snapshots
        self.manager.opponent_pool.update_elo(red_agent_id, new_red_elo)
        self.manager.opponent_pool.update_elo(blue_agent_id, new_blue_elo)

        return {
            "results": results,
            "outcome": outcome,
            "new_elo": {
                red_agent_id: new_red_elo,
                blue_agent_id: new_blue_elo
            }
        }

    def run_self_play_training_loop(
        self,
        agent_id: str,
        agent_instance: Any,
        team: str,
        episodes: int = 10,
        snapshot_frequency: int = 5,
        matchmaking_method: str = "random"
    ) -> Dict[str, Any]:
        """
        Trains the training agent against snapshots sampled from the opponent pool.
        Periodically creates newer self-snapshots to populate the opponent pool.
        """
        t_lower = team.lower()
        opponent_team = "blue" if t_lower == "red" else "red"
        
        # Ensure at least one opponent exists in the pool for matchmaking
        opponents = self.manager.opponent_pool.list_opponents(team=opponent_team)
        if not opponents:
            # Create a default baseline model snapshot as initial opponent
            base_opp_id = f"baseline_{opponent_team}"
            base_opp_instance = self.instantiate_agent(
                model_type="PPO" if "PPO" in agent_instance.__class__.__name__ else "DQN",
                team=opponent_team
            )
            self.manager.create_snapshot(base_opp_id, base_opp_instance, opponent_team)

        history = []
        win_count = 0
        draw_count = 0
        loss_count = 0

        for ep in range(1, episodes + 1):
            # Calculate win rate for progression scheduler
            total_matches = win_count + loss_count + draw_count
            win_rate = win_count / max(1, total_matches)

            # Sample opponent snapshot from the pool
            opp_info = self.scheduler.schedule_opponent(
                agent_id=agent_id,
                opponent_team=opponent_team,
                method=matchmaking_method,
                win_rate=win_rate
            )

            # Instantiate opponent agent and load snapshot weights
            opp_instance = self.instantiate_agent(opp_info["model_type"], opponent_team)
            self.manager.load_opponent_weights(opp_info["opponent_id"], opp_instance)

            # Run match: training agent learns (eval_mode=False)
            if t_lower == "red":
                match_res = self.run_match(
                    red_agent_id=agent_id,
                    red_agent=agent_instance,
                    blue_agent_id=opp_info["opponent_id"],
                    blue_agent=opp_instance,
                    eval_mode=False
                )
                outcome = match_res["outcome"] # red's outcome
            else:
                match_res = self.run_match(
                    red_agent_id=opp_info["opponent_id"],
                    red_agent=opp_instance,
                    blue_agent_id=agent_id,
                    blue_agent=agent_instance,
                    eval_mode=False
                )
                outcome = 1.0 - match_res["outcome"] # blue's outcome

            # Track win/loss metrics
            if outcome == 1.0:
                win_count += 1
            elif outcome == 0.0:
                loss_count += 1
            else:
                draw_count += 1

            # Log step history
            history.append({
                "episode": ep,
                "opponent": opp_info["opponent_id"],
                "outcome": outcome,
                "elo": self.manager.rating_system.get_rating(agent_id)
            })

            # Create snapshot of the training agent at the specified frequency
            if ep % snapshot_frequency == 0:
                self.manager.create_snapshot(agent_id, agent_instance, team)

        total = max(1, episodes)
        return {
            "win_rate": win_count / total,
            "loss_rate": loss_count / total,
            "draw_rate": draw_count / total,
            "final_elo": self.manager.rating_system.get_rating(agent_id),
            "history": history
        }
