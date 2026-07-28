import os
import sys
import torch
import numpy as np
import networkx as nx

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))

from stgnn_model import IEEE39STGNN
from grid_topology import GridTopology
from topology_analyzer import TopologyAnalyzer

class SpatioTemporalPropagationDetector:
    def __init__(self, model_path=None, device="cpu"):
        self.device = device
        
        # 1. Load topology and initialize structural analyzer
        self.topo = GridTopology()
        self.analyzer = TopologyAnalyzer(self.topo)
        
        # 2. Extract edge index and network parameters
        from gnn_trainer import extract_network_parameters
        self.edge_index, self.params = extract_network_parameters(self.topo)
        
        # 3. Initialize ST-GNN architecture
        self.model = IEEE39STGNN(
            edge_index=self.edge_index,
            hidden_dim=64
        )
        
        # 4. Load trained weights
        if model_path is None:
            model_path = os.path.join(current_dir, "trained_stgnn_model.pt")
            
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=device))
            print(f"Loaded trained ST-GNN model from: {model_path}")
        else:
            print(f"Warning: ST-GNN checkpoint not found at {model_path}. Running with default weights.")
            
        self.model.to(device)
        self.model.eval()
        
    def _prepare_inputs(self, seq_nodes):
        """
        seq_nodes shape: (20, 39, 4) or (batch, 20, 39, 4)
        Returns:
          x_seq: tensor (batch, 20, 39, 4)
          edge_seq: tensor (batch, 20, 46, 5)
        """
        if isinstance(seq_nodes, np.ndarray):
            x_seq = torch.tensor(seq_nodes, dtype=torch.float32)
        else:
            x_seq = seq_nodes.clone().detach()
            
        if x_seq.dim() == 3:
            x_seq = x_seq.unsqueeze(0) # add batch dim: (1, 20, 39, 4)
            
        batch_size = x_seq.size(0)
        seq_len = x_seq.size(1)
        
        # Compute edge features sequence-wise
        # We process step-by-step for the sequence length
        edge_seq_list = []
        for s in range(seq_len):
            V = x_seq[:, s, :, 2].cpu().numpy()
            theta = x_seq[:, s, :, 3].cpu().numpy()
            
            from gnn_trainer import compute_vectorized_flows
            P_flow, Q_flow, loading = compute_vectorized_flows(V, theta, self.params)
            
            line_status = np.zeros((batch_size, len(self.edge_index)))
            trafo_status = np.zeros((batch_size, len(self.edge_index)))
            for k in range(len(self.edge_index)):
                if self.params["is_trafo"][k]:
                    trafo_status[:, k] = 1.0
                else:
                    line_status[:, k] = 1.0
                    
            step_edges = np.stack([P_flow, Q_flow, loading / 100.0, line_status, trafo_status], axis=-1).astype(np.float32)
            edge_seq_list.append(step_edges)
            
        # Stack to (seq_len, batch, 46, 5) -> transpose to (batch, seq_len, 46, 5)
        edge_seq = np.stack(edge_seq_list, axis=0) # (20, batch, 46, 5)
        edge_seq = torch.tensor(edge_seq, dtype=torch.float32).transpose(0, 1).to(self.device)
        x_seq = x_seq.to(self.device)
        
        return x_seq, edge_seq

    def future_node_risk(self, seq):
        """
        Predicts future node risk at t + 5.
        seq: (20, 39, 4) or (batch, 20, 39, 4)
        """
        x_seq, edge_seq = self._prepare_inputs(seq)
        with torch.no_grad():
            pred_node_risk, _ = self.model(x_seq, edge_seq)
        return pred_node_risk.squeeze(0).cpu().numpy()

    def future_edge_risk(self, seq):
        """
        Predicts future edge risk at t + 5.
        seq: (20, 39, 4) or (batch, 20, 39, 4)
        """
        x_seq, edge_seq = self._prepare_inputs(seq)
        with torch.no_grad():
            _, pred_edge_risk = self.model(x_seq, edge_seq)
        return pred_edge_risk.squeeze(0).cpu().numpy()

    def forecast_next_failures(self, seq, top_n=5):
        """
        Identifies and ranks upcoming vulnerable buses and lines at t + 5.
        """
        node_risk = self.future_node_risk(seq)
        edge_risk = self.future_edge_risk(seq)
        
        # Format and rank critical buses
        critical_buses = []
        for i in range(39):
            # Fuse GNN future prediction (60%) with structural PageRank centrality (40%)
            struct_score = self.analyzer.vulnerability_scores()[i] # base structural centrality
            fused_score = 0.4 * struct_score + 0.6 * float(node_risk[i])
            critical_buses.append({
                "bus_id": i,
                "risk_score": float(fused_score)
            })
        critical_buses = sorted(critical_buses, key=lambda b: b["risk_score"], reverse=True)[:top_n]
        
        # Format and rank critical lines
        critical_lines = []
        edge_centrality = nx.edge_betweenness_centrality(self.analyzer.G)
        for k, (u, v) in enumerate(self.edge_index):
            struct_centrality = edge_centrality.get((u, v), edge_centrality.get((v, u), 0.0))
            dyn_risk = float(edge_risk[k])
            fused_score = 0.4 * struct_centrality * 46 + 0.6 * dyn_risk
            
            critical_lines.append({
                "from": int(u),
                "to": int(v),
                "line_id": self.topo.lines[k]["id"],
                "risk_score": fused_score
            })
        critical_lines = sorted(critical_lines, key=lambda l: l["risk_score"], reverse=True)[:top_n]
        
        return critical_buses, critical_lines

    def propagation_prediction(self, source_bus, target_bus):
        """
        Returns the shortest propagation path between source and target.
        """
        return self.analyzer.propagation_paths(source_bus, target_bus)

# Singleton helper for API usage
_detector = None

def _get_detector():
    global _detector
    if _detector is None:
        _detector = SpatioTemporalPropagationDetector()
    return _detector

def future_node_risk(seq):
    return _get_detector().future_node_risk(seq)

def future_edge_risk(seq):
    return _get_detector().future_edge_risk(seq)

def forecast_next_failures(seq, top_n=5):
    return _get_detector().forecast_next_failures(seq, top_n)

def propagation_prediction(source_bus, target_bus):
    return _get_detector().propagation_prediction(source_bus, target_bus)
