import sys
import os
import numpy as np
from typing import Dict, Any, Tuple

# Ensure parent directory is in path to import state encoder, environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from environment import SmartGridRLEnv
from state_encoder import StateEncoder

class MultiAgentGridEnv:
    def __init__(self, max_steps: int = 50, bus_count: int = 9):
        """
        Wrapper environment around SmartGridRLEnv providing MARL interfaces.
        """
        self.env = SmartGridRLEnv(max_steps=max_steps, bus_count=bus_count)
        self.encoder = StateEncoder(self.env.bus_ids, self.env.line_ids)
        self.state_dim = self.encoder.state_dim

    def reset(self) -> Dict[str, Any]:
        """
        Resets the underlying simulation.
        """
        return self.env.reset()

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float], bool, Dict[str, Any]]:
        """
        Transitions the grid simulation step using resolved actions dictionary.
        """
        return self.env.step(action)

    def get_raw_state(self) -> Dict[str, Any]:
        """
        Retrieves the raw simulation dictionary.
        """
        return self.env.get_state()

    def get_encoded_state(self) -> np.ndarray:
        """
        Returns normalized state vectors (67-dim).
        """
        return self.encoder.encode(self.env.get_state())

    @property
    def current_step(self) -> int:
        return self.env.current_step

    @property
    def max_steps(self) -> int:
        return self.env.max_steps
