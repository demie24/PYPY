import torch
import torch.nn as nn

class ThreatPredictorLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, dropout=0.2):
        """
        Lightweight LSTM Network for forecasting grid threat scores.
        """
        super(ThreatPredictorLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Recurrent Layer
        # batch_first=True expects shape (batch_size, seq_len, input_dim)
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # Dense mapping to a single output value (predicted threat score target)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # Initialize hidden and cell states with zeros on the matching device
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        # LSTM forward pass
        # out: shape (batch_size, seq_len, hidden_dim)
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the last time step in the sequence
        last_step_out = out[:, -1, :]
        
        # Generate linear projection value
        prediction = self.fc(last_step_out)
        return prediction

    def predict(self, x):
        """
        Helper method to run prediction in inference mode.
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
        return output
