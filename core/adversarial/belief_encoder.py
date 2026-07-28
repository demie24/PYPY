import torch
import torch.nn as nn
from typing import Tuple

class GRUBeliefEncoder(nn.Module):
    """
    recurrent Belief State Encoder executing:
    Observation_t + Action_t-1 -> GRU Cell -> Belief State b_t
    """
    def __init__(self, obs_dim: int = 293, action_dim: int = 5, hidden_dim: int = 64):
        super(GRUBeliefEncoder, self).__init__()
        self.hidden_dim = hidden_dim
        
        # Action embedding layer
        self.action_embed = nn.Embedding(action_dim, 16)
        
        # Input dimensionality to GRU is obs_dim + action_embed_dim
        self.gru_cell = nn.GRUCell(obs_dim + 16, hidden_dim)

    def forward(self, obs: torch.Tensor, prev_action: torch.Tensor, prev_belief: torch.Tensor) -> torch.Tensor:
        """
        Args:
            obs: Tensor of shape (batch, obs_dim)
            prev_action: LongTensor of shape (batch,) representing action indices
            prev_belief: Tensor of shape (batch, hidden_dim)
        Returns:
            belief: Tensor of shape (batch, hidden_dim)
        """
        act_embed = self.action_embed(prev_action)
        gru_input = torch.cat([obs, act_embed], dim=-1)
        
        # Output is the updated hidden state (belief state)
        new_belief = self.gru_cell(gru_input, prev_belief)
        return new_belief
