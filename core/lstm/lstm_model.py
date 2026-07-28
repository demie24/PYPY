import torch
import torch.nn as nn

class IEEE39LSTMClassifier(nn.Module):
    def __init__(self, input_dim=156, hidden_dim=64, num_layers=2, num_classes=8, dropout=0.2):
        super(IEEE39LSTMClassifier, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # LSTM Network
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # Fully Connected Classifier
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes)
        )
        
        # Normalization buffers
        self.register_buffer("mean", torch.zeros(input_dim))
        self.register_buffer("std", torch.ones(input_dim))
        
    def forward(self, x):
        """
        Forward pass of the LSTM classifier.
        Input x: (batch, seq_len, 156) or (seq_len, 156)
        """
        # Ensure 3D input shape (batch, seq_len, input_dim)
        if x.dim() == 2:
            x = x.unsqueeze(0)
            
        # Standardize features internally
        # x shape: (batch, seq_len, 156)
        # mean/std shape: (156,)
        mean_expanded = self.mean.view(1, 1, -1)
        std_expanded = self.std.view(1, 1, -1)
        x_norm = (x - mean_expanded) / (std_expanded + 1e-8)
        
        # Initialize hidden and cell states
        h0 = torch.zeros(self.num_layers, x_norm.size(0), self.hidden_dim).to(x_norm.device)
        c0 = torch.zeros(self.num_layers, x_norm.size(0), self.hidden_dim).to(x_norm.device)
        
        # LSTM forward pass
        out, _ = self.lstm(x_norm, (h0, c0))
        
        # Decode the hidden state of the last time step
        last_step_out = out[:, -1, :]
        
        # Get classification logits
        logits = self.fc(last_step_out)
        return logits
