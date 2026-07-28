import torch
import torch.nn as nn
import torch.nn.functional as F

class MPNNLayer(nn.Module):
    def __init__(self, node_in, edge_in, node_out):
        super(MPNNLayer, self).__init__()
        self.msg_fc = nn.Sequential(
            nn.Linear(node_in + edge_in, node_out),
            nn.ReLU()
        )
        self.node_fc = nn.Sequential(
            nn.Linear(node_in + node_out, node_out),
            nn.ReLU()
        )
        
    def forward(self, x, edge_feats, edge_index):
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

class IEEE39GNN(nn.Module):
    def __init__(self, edge_index, node_in=4, edge_in=5, hidden_dim=128, num_classes=8):
        super(IEEE39GNN, self).__init__()
        self.edge_index = edge_index
        self.num_classes = num_classes
        
        # Standardization buffers
        self.register_buffer("node_mean", torch.zeros(node_in))
        self.register_buffer("node_std", torch.ones(node_in))
        self.register_buffer("edge_mean", torch.zeros(edge_in))
        self.register_buffer("edge_std", torch.ones(edge_in))
        
        # MPNN layers
        self.layer1 = MPNNLayer(node_in, edge_in, hidden_dim)
        self.layer2 = MPNNLayer(hidden_dim, edge_in, hidden_dim)
        
        # Task 1: Classification Head with fused mean and max pooling
        self.class_fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, num_classes)
        )
        
        # Task 2: Node Risk Head
        self.node_risk_fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # Task 2: Edge Risk Head
        self.edge_risk_fc = nn.Sequential(
            nn.Linear(hidden_dim * 2 + edge_in, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x, edge_feats):
        """
        x: (batch, 39, 4)
        edge_feats: (batch, 46, 5)
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)
        if edge_feats.dim() == 2:
            edge_feats = edge_feats.unsqueeze(0)
            
        # Normalize inputs
        node_mean_expanded = self.node_mean.view(1, 1, -1)
        node_std_expanded = self.node_std.view(1, 1, -1)
        x_norm = (x - node_mean_expanded) / (node_std_expanded + 1e-8)
        
        edge_mean_expanded = self.edge_mean.view(1, 1, -1)
        edge_std_expanded = self.edge_std.view(1, 1, -1)
        edge_feats_norm = (edge_feats - edge_mean_expanded) / (edge_std_expanded + 1e-8)
        
        # Message passing
        h = self.layer1(x_norm, edge_feats_norm, self.edge_index)
        h = self.layer2(h, edge_feats_norm, self.edge_index) # (batch, 39, hidden_dim)
        
        # Node risk
        node_risk = self.node_risk_fc(h).squeeze(-1) # (batch, 39)
        
        # Edge risk
        from_nodes = [u for u, v in self.edge_index]
        to_nodes = [v for u, v in self.edge_index]
        h_from = h[:, from_nodes, :]
        h_to = h[:, to_nodes, :]
        edge_input = torch.cat([h_from, h_to, edge_feats_norm], dim=-1) # (batch, 46, hidden_dim * 2 + edge_in)
        edge_risk = self.edge_risk_fc(edge_input).squeeze(-1) # (batch, 46)
        
        # Fused Global Pooling: Mean + Max over nodes
        h_mean = torch.mean(h, dim=1)
        h_max = torch.max(h, dim=1)[0]
        h_pool = torch.cat([h_mean, h_max], dim=-1) # (batch, hidden_dim * 2)
        
        class_logits = self.class_fc(h_pool)
        
        return class_logits, node_risk, edge_risk
