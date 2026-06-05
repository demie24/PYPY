import torch
import numpy as np
from typing import Tuple, List, Any

class PPOMemory:
    def __init__(self, device: str = "cpu"):
        """
        Rollout memory buffer designed for PPO. Stores states, actions, log probabilities,
        rewards, state values, and terminal flags. Computes Generalized Advantage Estimation (GAE).
        """
        self.device = device
        self.clear()

    def store(
        self,
        state: np.ndarray,
        action: int,
        log_prob: float,
        reward: float,
        value: float,
        done: bool
    ):
        """
        Appends a transition step metadata payload to memory collections.
        """
        self.states.append(state)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)

    def clear(self):
        """
        Wipes all trajectory tracking lists to start fresh collection.
        """
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.log_probs: List[float] = []
        self.rewards: List[float] = []
        self.values: List[float] = []
        self.dones: List[bool] = []

    def compute_gae(
        self,
        next_value: float,
        gamma: float,
        gae_lambda: float
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes Generalized Advantage Estimation (GAE) and Target TD-Lambda Returns.
        Returns:
            advantages: Normalized advantage values.
            returns: Target values for training the Critic network.
        """
        # Append next value to align with rewards/dones length for terminal tracking
        values = self.values + [next_value]
        advantages = []
        gae = 0.0

        # Loop backwards through time to compute advantages recursively
        for step in reversed(range(len(self.rewards))):
            # Temporal Difference error: delta = r_t + gamma * V(s_{t+1}) * (1 - done_t) - V(s_t)
            delta = (
                self.rewards[step]
                + gamma * values[step + 1] * (1.0 - float(self.dones[step]))
                - values[step]
            )
            # GAE: A_t = delta_t + gamma * lambda * (1 - done_t) * A_{t+1}
            gae = delta + gamma * gae_lambda * (1.0 - float(self.dones[step])) * gae

            advantages.insert(0, gae)

        # Convert to numpy arrays, then tensors
        advantages_np = np.array(advantages, dtype=np.float32)
        values_np = np.array(self.values, dtype=np.float32)
        returns_np = advantages_np + values_np

        advantages_tensor = torch.from_numpy(advantages_np).to(self.device)
        returns_tensor = torch.from_numpy(returns_np).to(self.device)

        # Normalize advantages for training stability
        if advantages_tensor.numel() > 1:
            advantages_tensor = (advantages_tensor - advantages_tensor.mean()) / (
                advantages_tensor.std() + 1e-8
            )

        return advantages_tensor, returns_tensor

    def generate_batches(
        self,
        batch_size: int
    ) -> Tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        List[np.ndarray]
    ]:
        """
        Converts the stored trajectory lists into PyTorch Tensors and generates indices
        for shuffling and mini-batch partitioning.
        """
        n_states = len(self.states)
        
        # Convert lists to NumPy arrays first
        states_np = np.array(self.states, dtype=np.float32)
        actions_np = np.array(self.actions, dtype=np.int64)
        log_probs_np = np.array(self.log_probs, dtype=np.float32)
        values_np = np.array(self.values, dtype=np.float32)

        # Convert to PyTorch Tensors
        states_tensor = torch.from_numpy(states_np).to(self.device)
        actions_tensor = torch.from_numpy(actions_np).to(self.device)
        log_probs_tensor = torch.from_numpy(log_probs_np).to(self.device)
        values_tensor = torch.from_numpy(values_np).to(self.device)

        # Generate randomized mini-batch partition indices
        indices = np.arange(n_states)
        np.random.shuffle(indices)
        
        batches = []
        for start in range(0, n_states, batch_size):
            batches.append(indices[start : start + batch_size])

        return (
            states_tensor,
            actions_tensor,
            log_probs_tensor,
            values_tensor,
            batches
        )

    def __len__(self) -> int:
        return len(self.states)
