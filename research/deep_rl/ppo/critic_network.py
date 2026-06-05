import torch
import torch.nn as nn
import numpy as np
from typing import List

class CriticNetwork(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_layers: List[int] = None,
        activation: str = "relu",
        seed: int = None
    ):
        """
        PyTorch Critic Network implementation for Proximal Policy Optimization (PPO).
        Estimates the state value V(s) for a given state vector.
        """
        super(CriticNetwork, self).__init__()

        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)

        self.hidden_layers = hidden_layers or [128, 64]
        
        # Build hidden layers dynamically
        layers = []
        last_dim = input_dim
        for hidden_dim in self.hidden_layers:
            layers.append(nn.Linear(last_dim, hidden_dim))
            
            # Select activation function
            act = activation.lower()
            if act == "relu":
                layers.append(nn.ReLU())
            elif act == "tanh":
                layers.append(nn.Tanh())
            elif act == "sigmoid":
                layers.append(nn.Sigmoid())
            else:
                layers.append(nn.ReLU())
                
            last_dim = hidden_dim

        # Final state-value estimation output layer
        layers.append(nn.Linear(last_dim, 1))
        
        self.network = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Forward pass returning estimated state value V(s).
        """
        return self.network(state)
