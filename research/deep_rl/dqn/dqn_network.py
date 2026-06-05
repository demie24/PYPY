import torch
import torch.nn as nn
import numpy as np
from typing import List

class DQNNetwork(nn.Module):
    def __init__(
        self, 
        input_dim: int, 
        output_dim: int, 
        hidden_layers: List[int] = None, 
        activation: str = "relu", 
        seed: int = None
    ):
        """
        PyTorch Deep Q-Network implementation.
        """
        super(DQNNetwork, self).__init__()
        
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)

        self.hidden_layers = hidden_layers or [128, 64]
        
        # Build network layers dynamically
        layers = []
        last_dim = input_dim
        for hidden_dim in self.hidden_layers:
            layers.append(nn.Linear(last_dim, hidden_dim))
            
            # Select activation function
            if activation == "relu":
                layers.append(nn.ReLU())
            elif activation == "tanh":
                layers.append(nn.Tanh())
            elif activation == "sigmoid":
                layers.append(nn.Sigmoid())
            else:
                layers.append(nn.ReLU())  # Fallback to ReLU
                
            last_dim = hidden_dim
            
        # Final output layer providing Q-value projections for each discrete action
        layers.append(nn.Linear(last_dim, output_dim))
        
        self.network = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Forward pass to compute Q-values.
        """
        return self.network(state)
