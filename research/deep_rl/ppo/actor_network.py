import torch
import torch.nn as nn
import numpy as np
from typing import List

class ActorNetwork(nn.Module):
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_layers: List[int] = None,
        activation: str = "relu",
        seed: int = None
    ):
        """
        PyTorch Actor Network implementation for Proximal Policy Optimization (PPO).
        Maps encoded state vectors to categorical action probability distributions.
        """
        super(ActorNetwork, self).__init__()

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

        # Categorical logits projection layer
        self.feature_net = nn.Sequential(*layers)
        self.logits_layer = nn.Linear(last_dim, output_dim)
        
        # Softmax layer for output probabilities
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Forward pass returning action probability distribution.
        """
        features = self.feature_net(state)
        logits = self.logits_layer(features)
        return self.softmax(logits)

    def get_logits(self, state: torch.Tensor) -> torch.Tensor:
        """
        Returns raw logit outputs for numerical stability during distribution sampling/learning.
        """
        features = self.feature_net(state)
        return self.logits_layer(features)
