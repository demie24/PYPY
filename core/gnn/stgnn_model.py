import torch
import torch.nn as nn
import torch.nn.functional as F

class TemporalLSTM(nn.Module):
    def __init__(self, in_dim, hidden_dim, num_layers=1):
        super(TemporalLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=in_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )
        
    def forward(self, x):
        """
        x shape: (batch_size * num_elements, seq_len, in_dim)
        Returns: (batch_size * num_elements, hidden_dim)
        """
        out, _ = self.lstm(x)
        # Return the hidden state of the last time step
        return out[:, -1, :]

class SpatialMPNN(nn.Module):
    def __init__(self, node_in, edge_in, node_out):
        super(SpatialMPNN, self).__init__()
        self.msg_fc = nn.Sequential(
            nn.Linear(node_in + edge_in, node_out),
            nn.ReLU()
        )
        self.node_fc = nn.Sequential(
            nn.Linear(node_in + node_out, node_out),
            nn.ReLU()
        )
        
    def forward(self, x, edge_feats, edge_index):
        """
        x: (batch, 39, node_in)
        edge_feats: (batch, 46, edge_in)
        edge_index: list of 46 tuples (from_bus, to_bus)
        """
        batch_size = x.size(0)
        num_nodes = x.size(1)
        num_edges = len(edge_index)
        
        from_nodes = [u for u, v in edge_index]
        to_nodes = [v for u, v in edge_index]
        
        x_from = x[:, from_nodes, :]
        x_to = x[:, to_nodes, :]
        
        # Message from -> to
        msg_input_f2t = torch.cat([x_from, edge_feats], dim=-1)
        msg_f2t = self.msg_fc(msg_input_f2t)
        
        # Message to -> from (flip signs of P and Q flow for reverse direction)
        edge_feats_rev = edge_feats.clone()
        if edge_feats_rev.size(-1) >= 2:
            edge_feats_rev[:, :, 0] = -edge_feats_rev[:, :, 0]
            edge_feats_rev[:, :, 1] = -edge_feats_rev[:, :, 1]
            
        msg_input_t2f = torch.cat([x_to, edge_feats_rev], dim=-1)
        msg_t2f = self.msg_fc(msg_input_t2f)
        
        # Aggregate messages
        agg_msg = torch.zeros(batch_size, num_nodes, msg_f2t.size(-1), device=x.device)
        for k in range(num_edges):
            u, v = edge_index[k]
            agg_msg[:, v, :] += msg_f2t[:, k, :]
            agg_msg[:, u, :] += msg_t2f[:, k, :]
            
        out = self.node_fc(torch.cat([x, agg_msg], dim=-1))
        return out

class IEEE39STGNN(nn.Module):
    def __init__(self, edge_index, node_in=4, edge_in=5, seq_len=20, hidden_dim=64):
        super(IEEE39STGNN, self).__init__()
        self.edge_index = edge_index
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        
        # Input normalization buffers
        self.register_buffer("node_mean", torch.zeros(node_in))
        self.register_buffer("node_std", torch.ones(node_in))
        self.register_buffer("edge_mean", torch.zeros(edge_in))
        self.register_buffer("edge_std", torch.ones(edge_in))
        
        # Temporal Module: LSTM feature extractors
        self.node_temporal = TemporalLSTM(node_in, hidden_dim, num_layers=1)
        self.edge_temporal = TemporalLSTM(edge_in, hidden_dim, num_layers=1)
        
        # Spatial Module: MPNN layers
        self.spatial1 = SpatialMPNN(hidden_dim, hidden_dim, hidden_dim)
        self.spatial2 = SpatialMPNN(hidden_dim, hidden_dim, hidden_dim)
        
        # Predictors for Future Node/Edge Risks (at t + 5)
        self.node_risk_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.edge_risk_head = nn.Sequential(
            nn.Linear(hidden_dim * 2 + hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x_seq, edge_seq):
        """
        x_seq: Node feature sequences (batch, seq_len, 39, 4)
        edge_seq: Edge feature sequences (batch, seq_len, 46, 5)
        """
        batch_size = x_seq.size(0)
        
        # 1. Standardize node and edge features sequence-wise
        node_mean_expanded = self.node_mean.view(1, 1, 1, -1)
        node_std_expanded = self.node_std.view(1, 1, 1, -1)
        x_seq_norm = (x_seq - node_mean_expanded) / (node_std_expanded + 1e-8)
        
        edge_mean_expanded = self.edge_mean.view(1, 1, 1, -1)
        edge_std_expanded = self.edge_std.view(1, 1, 1, -1)
        edge_seq_norm = (edge_seq - edge_mean_expanded) / (edge_std_expanded + 1e-8)
        
        # 2. Extract Temporal Features using node and edge LSTMs
        # Reshape for node LSTM: (batch * 39, seq_len, 4)
        x_reshaped = x_seq_norm.transpose(1, 2).contiguous().view(batch_size * 39, self.seq_len, -1)
        h_node_temp = self.node_temporal(x_reshaped) # (batch * 39, hidden_dim)
        h_node = h_node_temp.view(batch_size, 39, -1) # (batch, 39, hidden_dim)
        
        # Reshape for edge LSTM: (batch * 46, seq_len, 5)
        edge_reshaped = edge_seq_norm.transpose(1, 2).contiguous().view(batch_size * 46, self.seq_len, -1)
        h_edge_temp = self.edge_temporal(edge_reshaped) # (batch * 46, hidden_dim)
        h_edge = h_edge_temp.view(batch_size, 46, -1) # (batch, 46, hidden_dim)
        
        # 3. Propagate spatial message passing
        h_space = self.spatial1(h_node, h_edge, self.edge_index)
        h_space = self.spatial2(h_space, h_edge, self.edge_index) # (batch, 39, hidden_dim)
        
        # 4. Predict Future Node Risk
        pred_node_risk = self.node_risk_head(h_space).squeeze(-1) # (batch, 39)
        
        # 5. Predict Future Edge Risk
        from_nodes = [u for u, v in self.edge_index]
        to_nodes = [v for u, v in self.edge_index]
        h_space_from = h_space[:, from_nodes, :]
        h_space_to = h_space[:, to_nodes, :]
        
        # Concatenate edge endpoints and the temporal edge embedding
        edge_pred_input = torch.cat([h_space_from, h_space_to, h_edge], dim=-1) # (batch, 46, hidden_dim * 3)
        pred_edge_risk = self.edge_risk_head(edge_pred_input).squeeze(-1) # (batch, 46)
        
        return pred_node_risk, pred_edge_risk
