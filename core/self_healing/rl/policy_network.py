import torch
import torch.nn as nn
import torch.nn.functional as F

class PolicyNetwork(nn.Module):
    """
    Actor network for PPO. Maps the 72-dimensional grid state vector
    to a categorical probability distribution over the 10 discrete actions.
    """
    def __init__(self, state_dim: int = 72, action_dim: int = 10):
        super(PolicyNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim, 64)
        self.fc2 = nn.Linear(64, 64)
        self.actor_head = nn.Linear(64, action_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape: (batch_size, state_dim) or (state_dim,)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        logits = self.actor_head(x)
        return logits
