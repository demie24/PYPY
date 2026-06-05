import os
import sys
import numpy as np
from typing import Dict, Any, List, Optional

# Ensure parent directory is in path to import ModelManager, DQN/PPO configs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dqn")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ppo")))

from model_manager import ModelManager
from dqn_red_agent import DQNRedAgent
from dqn_blue_agent import DQNBlueAgent
from ppo_config import PPOConfig
from ppo_red_agent import PPORedAgent
from ppo_blue_agent import PPOBlueAgent

from opponent_pool import OpponentPool
from rating_system import RatingSystem

class SelfPlayManager:
    def __init__(
        self,
        opponent_pool: Optional[OpponentPool] = None,
        rating_system: Optional[RatingSystem] = None,
        checkpoint_dir: Optional[str] = None
    ):
        """
        Coordinates agent snapshot weight preservation and ELO league progression.
        """
        self.opponent_pool = opponent_pool or OpponentPool()
        self.rating_system = rating_system or RatingSystem()
        self.model_manager = ModelManager(checkpoint_dir)
        self.snapshot_counter = 0

    def create_snapshot(self, agent_id: str, agent_instance: Any, team: str) -> str:
        """
        Serializes current training agent weights to persistent storage and adds
        metadata to the opponent pool.
        """
        self.snapshot_counter += 1
        snapshot_name = f"{agent_id}_snap_{self.snapshot_counter}"
        
        # Save weights using ModelManager
        checkpoint_path = agent_instance.save_model(snapshot_name)
        
        # Determine model class type
        model_type = "DQN"
        if "PPO" in agent_instance.__class__.__name__:
            model_type = "PPO"
            
        current_elo = self.rating_system.get_rating(agent_id)
        
        # Save snapshot reference in opponent pool
        self.opponent_pool.add_opponent(
            opponent_id=snapshot_name,
            model_type=model_type,
            team=team,
            checkpoint_name=snapshot_name,
            elo=current_elo
        )
        
        # Initialize Elo tracking for the new snapshot
        self.rating_system.set_rating(snapshot_name, current_elo)
        return snapshot_name

    def load_opponent_weights(self, opponent_id: str, agent_instance: Any) -> None:
        """
        Loads weight parameters from a registered snapshot ID into an agent instance.
        """
        opp_info = self.opponent_pool.get_opponent(opponent_id)
        if not opp_info:
            raise KeyError(f"Opponent snapshot '{opponent_id}' not found in pool.")
            
        # Temporarily re-point agent model manager base dir to find snapshot
        original_base_dir = agent_instance.model_manager.base_dir
        agent_instance.model_manager.base_dir = self.model_manager.base_dir
        
        try:
            agent_instance.load_model(opp_info["checkpoint_name"])
        finally:
            agent_instance.model_manager.base_dir = original_base_dir
