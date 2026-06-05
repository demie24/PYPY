import torch
import numpy as np
import sys
import os
from typing import Tuple, List, Any

# Ensure parent directory is in path to import ExperienceBuffer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from experience_buffer import ExperienceBuffer

class DQNReplayMemory(ExperienceBuffer):
    def __init__(self, capacity: int = 100000, device: str = "cpu"):
        super(DQNReplayMemory, self).__init__(capacity=capacity)
        self.device = device

    def sample_tensors(self, batch_size: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Samples a batch of experiences and converts them into optimized PyTorch Tensors.
        Returns:
            states: (batch_size, state_dim)
            actions: (batch_size, 1)
            rewards: (batch_size, 1)
            next_states: (batch_size, state_dim)
            dones: (batch_size, 1)
        """
        batch = self.sample(batch_size)
        
        states, actions, rewards, next_states, dones = zip(*batch)

        # Convert tuples/lists to NumPy arrays first to avoid PyTorch warning for efficiency
        states_np = np.array(states, dtype=np.float32)
        actions_np = np.array(actions, dtype=np.int64)
        rewards_np = np.array(rewards, dtype=np.float32)
        next_states_np = np.array(next_states, dtype=np.float32)
        dones_np = np.array(dones, dtype=np.float32)

        # Cast to PyTorch Tensors and send to targets device
        states_tensor = torch.from_numpy(states_np).to(self.device)
        actions_tensor = torch.from_numpy(actions_np).unsqueeze(1).to(self.device)
        rewards_tensor = torch.from_numpy(rewards_np).unsqueeze(1).to(self.device)
        next_states_tensor = torch.from_numpy(next_states_np).to(self.device)
        dones_tensor = torch.from_numpy(dones_np).unsqueeze(1).to(self.device)

        return states_tensor, actions_tensor, rewards_tensor, next_states_tensor, dones_tensor
