import torch
import torch.nn as nn

class MultiBusPredictorLSTM(nn.Module):
    def __init__(self, input_dim, output_dim=5, hidden_dim=64, num_layers=2, dropout=0.2):
        """
        Lightweight multi-output LSTM Network for forecasting multiple bus voltage trajectories.
        """
        super(MultiBusPredictorLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Shared temporal encoder (LSTM)
        # batch_first=True expects shape (batch_size, seq_len, input_dim)
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # Dense output mapping to predict all target buses simultaneously
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        # Initialize hidden and cell states on matching device
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        # LSTM forward pass
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the last time step in the sequence
        last_step_out = out[:, -1, :]
        
        # Generate multi-target projection output
        prediction = self.fc(last_step_out)
        return prediction

    def predict(self, x):
        """
        Helper method to run prediction in evaluation mode.
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
        return output
