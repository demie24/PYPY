import torch
import torch.nn as nn

class TelemetryPredictorLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, dropout=0.2):
        """
        Lightweight LSTM Network for forecasting grid telemetry parameters (e.g. Bus voltages).
        """
        super(TelemetryPredictorLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        # LSTM forward pass
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the last time step in the sequence
        last_step_out = out[:, -1, :]
        
        # Linear projection value (e.g. predicted Bus_5 voltage)
        prediction = self.fc(last_step_out)
        return prediction

    def predict(self, x):
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
        return output
