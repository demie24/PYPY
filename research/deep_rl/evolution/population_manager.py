import os
import sys
from typing import Dict, Any, List, Optional

# Ensure parent directories are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dqn")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ppo")))

from dqn_red_agent import DQNRedAgent
from dqn_blue_agent import DQNBlueAgent
from ppo_config import PPOConfig
from ppo_red_agent import PPORedAgent
from ppo_blue_agent import PPOBlueAgent
from model_manager import ModelManager

class PopulationManager:
    def __init__(self, checkpoint_dir: Optional[str] = None):
        """
        Manages population configuration, creation, and generational persistence.
        """
        self.model_manager = ModelManager(checkpoint_dir)
        self.population: Dict[str, Any] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {} # id -> {model_type, team}

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

        agent.model_manager.base_dir = self.model_manager.base_dir
        return agent

    def create_population(self, size: int, model_type: str, team: str) -> List[str]:
        """
        Creates a new population of agents of specified type and team.
        """
        self.population.clear()
        self.metadata.clear()
        
        agent_ids = []
        for i in range(size):
            agent_id = f"agent_{team.lower()}_{model_type.lower()}_{i}"
            agent = self.instantiate_agent(model_type, team)
            
            self.population[agent_id] = agent
            self.metadata[agent_id] = {
                "model_type": model_type.upper(),
                "team": team.lower()
            }
            agent_ids.append(agent_id)
        return agent_ids

    def register_agent(self, agent_id: str, agent_instance: Any, model_type: str, team: str) -> None:
        """
        Registers an existing agent instance to the population.
        """
        self.population[agent_id] = agent_instance
        self.metadata[agent_id] = {
            "model_type": model_type.upper(),
            "team": team.lower()
        }

    def remove_agent(self, agent_id: str) -> None:
        if agent_id in self.population:
            del self.population[agent_id]
        if agent_id in self.metadata:
            del self.metadata[agent_id]

    def get_agent(self, agent_id: str) -> Optional[Any]:
        return self.population.get(agent_id)

    def save_generation(self, generation_num: int) -> None:
        """
        Saves all agents in the current population under a generation checkpoint path.
        """
        for agent_id, agent in self.population.items():
            checkpoint_name = f"gen_{generation_num}_{agent_id}"
            agent.save_model(checkpoint_name)

    def load_generation(self, generation_num: int, agent_ids: List[str]) -> None:
        """
        Loads all agent weights in the current population from a generation checkpoint.
        """
        for agent_id in agent_ids:
            if agent_id in self.population:
                checkpoint_name = f"gen_{generation_num}_{agent_id}"
                self.population[agent_id].load_model(checkpoint_name)
