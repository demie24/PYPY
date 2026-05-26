import torch
import torch.nn as nn

class PredictionHead(nn.Module):
    def __init__(self, hidden_dim=128, output_dim=38):
        super(PredictionHead, self).__init__()
        self.fc1 = nn.Linear(hidden_dim, 128)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_dim)
        self.proj = nn.Linear(hidden_dim, 128)
        
    def forward(self, x):
        # Residual connection mapping input hidden representation to intermediate layer
        h1 = self.relu(self.fc1(x))
        h2 = self.relu(self.fc2(h1) + self.proj(x))
        return self.fc3(h2)

class PhysicsInformedPredictorLSTM(nn.Module):
    def __init__(self, input_dim=82, hidden_dim=128, num_layers=2, output_dim=38):
        super(PhysicsInformedPredictorLSTM, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.15 if num_layers > 1 else 0.0
        )
        
        # Three distinct prediction heads for t+10, t+30, and t+60 with residual connections
        self.head_10 = PredictionHead(hidden_dim, output_dim)
        self.head_30 = PredictionHead(hidden_dim, output_dim)
        self.head_60 = PredictionHead(hidden_dim, output_dim)
        
    def forward(self, x):
        # x shape: (batch, seq_len, input_dim)
        lstm_out, _ = self.lstm(x)
        
        # We use the final hidden state of the last LSTM layer
        # lstm_out shape: (batch, seq_len, hidden_dim)
        # We take the output at the last time step: lstm_out[:, -1, :]
        last_step = lstm_out[:, -1, :]
        
        out_10 = self.head_10(last_step)
        out_30 = self.head_30(last_step)
        out_60 = self.head_60(last_step)
        
        return out_10, out_30, out_60
