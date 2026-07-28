import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Any, Tuple

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))

from grid_topology import GridTopology

class GCNConvNative(nn.Module):
    """
    Native PyTorch implementation of GCN Message Passing layer.
    Computes H^(l+1) = ReLU( D^-1/2 (A + I) D^-1/2 H^(l) W )
    """
    def __init__(self, in_features: int, out_features: int):
        super(GCNConvNative, self).__init__()
        self.fc = nn.Linear(in_features, out_features, bias=True)
        
    def forward(self, x: torch.Tensor, norm_adj: torch.Tensor) -> torch.Tensor:
        # x: (batch, num_nodes, in_features)
        # norm_adj: (num_nodes, num_nodes)
        h = self.fc(x) # (batch, num_nodes, out_features)
        out = torch.matmul(norm_adj, h) # (batch, num_nodes, out_features)
        return F.relu(out)

class GATConvNative(nn.Module):
    """
    Native PyTorch implementation of Graph Attention Network (GAT) layer.
    """
    def __init__(self, in_features: int, out_features: int):
        super(GATConvNative, self).__init__()
        self.fc = nn.Linear(in_features, out_features, bias=False)
        self.a = nn.Parameter(torch.zeros(2 * out_features, 1))
        nn.init.xavier_uniform_(self.a.data, gain=1.414)
        
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        batch_size, num_nodes, _ = x.size()
        h = self.fc(x) # (batch, num_nodes, out_features)
        
        # Self-attention calculation (vectorized)
        h_i = h.unsqueeze(2).repeat(1, 1, num_nodes, 1) # (batch, num_nodes, num_nodes, out_features)
        h_j = h.unsqueeze(1).repeat(1, num_nodes, 1, 1) # (batch, num_nodes, num_nodes, out_features)
        h_cat = torch.cat([h_i, h_j], dim=-1) # (batch, num_nodes, num_nodes, 2 * out_features)
        
        scores = torch.matmul(h_cat, self.a).squeeze(-1) # (batch, num_nodes, num_nodes)
        scores = F.leaky_relu(scores, negative_slope=0.2)
        
        # Mask out non-edges (where adj is 0)
        zero_vec = -9e15 * torch.ones_like(scores)
        scores = torch.where(adj.unsqueeze(0) > 0, scores, zero_vec)
        
        attn = F.softmax(scores, dim=-1) # (batch, num_nodes, num_nodes)
        out = torch.bmm(attn, h) # (batch, num_nodes, out_features)
        return F.relu(out)

class TelemetryReconstructionGAE(nn.Module):
    """
    Graph Autoencoder (GAE) for Grid Telemetry Reconstruction.
    Encoder maps masked bus features to latent z.
    Decoder recovers full voltage (V), angle (theta), active power (P), reactive power (Q), and line loadings.
    """
    def __init__(self, edge_index, num_nodes=39, in_features=4, hidden_dim=64):
        super(TelemetryReconstructionGAE, self).__init__()
        self.num_nodes = num_nodes
        self.hidden_dim = hidden_dim
        
        # Build adjacency matrix
        adj = torch.zeros(num_nodes, num_nodes)
        for u, v in edge_index:
            adj[u, v] = 1.0
            adj[v, u] = 1.0
        self.register_buffer("adj", adj)
        
        # Normalised adjacency matrix for GCN
        adj_loop = adj + torch.eye(num_nodes)
        deg = torch.sum(adj_loop, dim=1)
        deg_inv_sqrt = torch.pow(deg, -0.5)
        deg_inv_sqrt[torch.isinf(deg_inv_sqrt)] = 0.0
        D_inv_sqrt = torch.diag(deg_inv_sqrt)
        norm_adj = torch.matmul(D_inv_sqrt, torch.matmul(adj_loop, D_inv_sqrt))
        self.register_buffer("norm_adj", norm_adj)
        
        # Encoder (GCN Conv + GAT Conv)
        self.enc_gcn = GCNConvNative(in_features, hidden_dim)
        self.enc_gat = GATConvNative(hidden_dim, hidden_dim)
        
        # Decoder - Reconstruct Node Telemetry (P, Q, V, theta)
        self.dec_node_val = nn.Linear(hidden_dim, 4)
        # Uncertainty estimation head (standard deviations output)
        self.dec_node_var = nn.Sequential(
            nn.Linear(hidden_dim, 4),
            nn.Softplus() # guarantees variance > 0
        )
        
        # Decoder - Reconstruct Edge Telemetry (Line loading for the 46 lines)
        self.dec_edge_val = nn.Linear(2 * hidden_dim, 1)
        self.dec_edge_var = nn.Sequential(
            nn.Linear(2 * hidden_dim, 1),
            nn.Softplus()
        )
        
        self.edge_index = edge_index

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        x: (batch, 39, 4) - partial/masked node features
        Returns:
            recon_nodes: reconstructed (P, Q, V, theta)
            node_std: node estimation uncertainty
            recon_edges: reconstructed edge loading
            edge_std: edge estimation uncertainty
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)
            
        # Encoder
        z1 = self.enc_gcn(x, self.norm_adj)
        z = self.enc_gat(z1, self.adj) # (batch, 39, hidden_dim)
        
        # Decode nodes
        recon_nodes = self.dec_node_val(z)
        node_std = self.dec_node_var(z) + 1e-4
        
        # Decode edges (pair-wise node concatenation)
        from_nodes = [u for u, v in self.edge_index]
        to_nodes = [v for u, v in self.edge_index]
        z_from = z[:, from_nodes, :]
        z_to = z[:, to_nodes, :]
        z_edge = torch.cat([z_from, z_to], dim=-1) # (batch, 46, 2 * hidden_dim)
        
        recon_edges = self.dec_edge_val(z_edge).squeeze(-1)
        edge_std = self.dec_edge_var(z_edge).squeeze(-1) + 1e-4
        
        return recon_nodes, node_std, recon_edges, edge_std

class PinnPhysicsValidator:
    """
    Physics-Informed Neural Network (PINN) validator checks Kirchhoff's laws
    and power flow consistency on the reconstructed telemetry.
    """
    def __init__(self, topo: GridTopology):
        self.topo = topo
        from gnn_trainer import extract_network_parameters
        _, self.params = extract_network_parameters(topo)
        
    def validate(self, V: np.ndarray, theta: np.ndarray, P: np.ndarray, Q: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        Validates telemetry arrays against grid power flow equations.
        V: (39,)
        theta: (39,)
        P: (39,) pu
        Q: (39,) pu
        
        Returns:
            is_valid: bool
            residuals: array of KCL active power mismatch at each bus.
        """
        from gnn_trainer import compute_vectorized_flows
        
        V_b = V.reshape(1, 39)
        theta_b = theta.reshape(1, 39)
        
        # Compute branch flows
        P_flow, Q_flow, _ = compute_vectorized_flows(V_b, theta_b, self.params)
        P_flow = P_flow[0]
        Q_flow = Q_flow[0]
        
        residuals_P = np.zeros(39)
        f_bus = self.params["f_bus"]
        t_bus = self.params["t_bus"]
        
        # Kirchhoff's Current Law: P_inj = sum of flows leaving node
        for i in range(39):
            net_flow = 0.0
            for k in range(len(f_bus)):
                if f_bus[k] == i:
                    net_flow += P_flow[k]
                elif t_bus[k] == i:
                    net_flow -= P_flow[k]
            residuals_P[i] = P[i] - net_flow
            
        # Physical consistency check
        max_residual = np.max(np.abs(residuals_P))
        # Reject if maximum bus active mismatch exceeds 0.20 pu
        is_valid = float(max_residual) < 0.20
        return is_valid, residuals_P

def integrate_trust_reconstruction(worker, bus_id: int, confidence_score: float) -> float:
    """
    Trust Fusion Integration (V10.3).
    Adjusts V10.1 MQTT verification worker trust based on GAE reconstruction confidence.
    """
    if bus_id not in worker.bus_states:
        worker.bus_states[bus_id] = {
            "last_sequence": 0,
            "last_hash": "0" * 64,
            "seen_nonces": set(),
            "trust_score": 1.0
        }
        
    state = worker.bus_states[bus_id]
    trust = state["trust_score"]
    
    if confidence_score > 0.90:
        trust = min(1.0, trust + 0.02)
    elif confidence_score < 0.50:
        # Penalize trust for high-uncertainty nodes
        trust = max(0.0, trust - 0.05)
        
    state["trust_score"] = trust
    return trust

def virtualize_blue_observation(
    masked_obs: np.ndarray,
    reconstructed_state: np.ndarray,
    missing_mask: np.ndarray
) -> np.ndarray:
    """
    Blue Agent Integration (V10.3).
    Replaces missing telemetry values in observation with GAE reconstructed estimates
    so that the PPO Blue Agent can continue running stateful defenses.
    """
    clean_obs = masked_obs.copy()
    
    # physical parameters are at index 0:124
    # Slices mapping:
    # 0:39 -> voltages
    # 39:78 -> active power injections
    # 78:124 -> loadings
    
    # 1. Voltages
    missing_volts = missing_mask[0:39]
    clean_obs[0:39] = np.where(missing_volts, reconstructed_state[0:39], clean_obs[0:39])
    
    # 2. Injections
    missing_injs = missing_mask[39:78]
    clean_obs[39:78] = np.where(missing_injs, reconstructed_state[39:78], clean_obs[39:78])
    
    # 3. Loadings
    missing_loadings = missing_mask[78:124]
    clean_obs[78:124] = np.where(missing_loadings, reconstructed_state[78:124], clean_obs[78:124])
    
    return clean_obs
