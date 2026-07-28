import torch
import torch.nn as nn

class IEEE39PINNAutoencoder(nn.Module):
    def __init__(self, input_dim=156, hidden_dim=64):
        super(IEEE39PINNAutoencoder, self).__init__()
        
        # Encoder Network
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, hidden_dim),
            nn.ReLU()
        )
        
        # Decoder Network
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, input_dim)
        )
        
        # Normalization buffers (will be updated during training)
        self.register_buffer("mean", torch.zeros(input_dim))
        self.register_buffer("std", torch.ones(input_dim))
        
    def forward(self, x):
        """
        Forward pass of the autoencoder.
        Input x: (batch, 156) where columns are:
            0-38: P (MW)
            39-77: Q (Mvar)
            78-116: V (pu)
            117-155: theta (rad)
        Returns:
            reconstructed: (batch, 156) reconstructed features
            P: (batch, 39) reconstructed P
            Q: (batch, 39) reconstructed Q
            V: (batch, 39) reconstructed V
            theta: (batch, 39) reconstructed theta
        """
        # Normalize input internally using mean and std buffers
        x_norm = (x - self.mean) / (self.std + 1e-8)
        
        latent = self.encoder(x_norm)
        reconstructed_norm = self.decoder(latent)
        
        # Denormalize output internally
        reconstructed = reconstructed_norm * (self.std + 1e-8) + self.mean
        
        # Split outputs
        pred_P = reconstructed[:, 0:39]
        pred_Q = reconstructed[:, 39:78]
        pred_V = reconstructed[:, 78:117]
        pred_theta = reconstructed[:, 117:156]
        
        return reconstructed, pred_P, pred_Q, pred_V, pred_theta


