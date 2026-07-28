import os
import sys
import torch
import torch.nn.functional as F
import numpy as np
import networkx as nx

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))

from gnn_model import IEEE39GNN
from gnn_evaluator import INV_LABEL_MAP
from topology_analyzer import TopologyAnalyzer
from grid_topology import GridTopology

class GraphAnomalyDetector:
    def __init__(self, model_path=None, device="cpu"):
        self.device = device
        
        # 1. Load topology and initialize analyzer
        self.topo = GridTopology()
        self.analyzer = TopologyAnalyzer(self.topo)
        
        # 2. Extract edge index and branch parameters
        from gnn_trainer import extract_network_parameters
        self.edge_index, self.params = extract_network_parameters(self.topo)
        
        # 3. Initialize GNN architecture with correct hidden_dim = 128
        self.model = IEEE39GNN(
            edge_index=self.edge_index,
            hidden_dim=128,
            num_classes=8
        )
        
        # 4. Load trained weights if available
        if model_path is None:
            model_path = os.path.join(current_dir, "trained_gnn_model.pt")
            
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=device))
            print(f"Loaded trained GNN model from: {model_path}")
        else:
            print(f"Warning: GNN model checkpoint not found at {model_path}. Running with random weights.")
            
        self.model.to(device)
        self.model.eval()
        
    def _prepare_inputs(self, x, edge_feats=None):
        """
        Converts inputs to tensors and computes edge features if not provided.
        x: array/tensor of shape (39, 4) or (batch, 39, 4)
        """
        if isinstance(x, np.ndarray):
            x_tensor = torch.tensor(x, dtype=torch.float32).to(self.device)
        else:
            x_tensor = x.to(self.device)
            
        if x_tensor.dim() == 2:
            x_tensor = x_tensor.unsqueeze(0) # (1, 39, 4)
            
        if edge_feats is None:
            V = x_tensor[:, :, 2].cpu().numpy()
            theta = x_tensor[:, :, 3].cpu().numpy()
            
            from gnn_trainer import compute_vectorized_flows
            P_flow, Q_flow, loading = compute_vectorized_flows(V, theta, self.params)
            
            N = x_tensor.size(0)
            line_status = np.zeros((N, len(self.edge_index)))
            trafo_status = np.zeros((N, len(self.edge_index)))
            for k in range(len(self.edge_index)):
                if self.params["is_trafo"][k]:
                    trafo_status[:, k] = 1.0
                else:
                    line_status[:, k] = 1.0
                    
            edge_feats_np = np.stack([P_flow, Q_flow, loading / 100.0, line_status, trafo_status], axis=-1).astype(np.float32)
            edge_feats_tensor = torch.tensor(edge_feats_np, dtype=torch.float32).to(self.device)
        else:
            if isinstance(edge_feats, np.ndarray):
                edge_feats_tensor = torch.tensor(edge_feats, dtype=torch.float32).to(self.device)
            else:
                edge_feats_tensor = edge_feats.to(self.device)
            if edge_feats_tensor.dim() == 2:
                edge_feats_tensor = edge_feats_tensor.unsqueeze(0)
                
        return x_tensor, edge_feats_tensor

    def classification(self, x, edge_feats=None):
        """
        Predicts the grid category (string) for the current state.
        """
        x_tensor, edge_feats_tensor = self._prepare_inputs(x, edge_feats)
        
        with torch.no_grad():
            logits, _, _ = self.model(x_tensor, edge_feats_tensor)
            probs = F.softmax(logits, dim=-1)
            pred = torch.argmax(probs, dim=-1).cpu().numpy()
            
        if len(pred) == 1:
            return INV_LABEL_MAP[int(pred[0])]
        return [INV_LABEL_MAP[int(p)] for p in pred]

    def risk_scores(self, x, edge_feats=None):
        """
        Computes dynamic node and edge risk scores using GNN predictions.
        """
        x_tensor, edge_feats_tensor = self._prepare_inputs(x, edge_feats)
        
        with torch.no_grad():
            _, node_risk, edge_risk = self.model(x_tensor, edge_feats_tensor)
            
        return node_risk.squeeze(0).cpu().numpy(), edge_risk.squeeze(0).cpu().numpy()

    def critical_components(self, x, edge_feats=None, top_n=5):
        """
        Identifies top critical buses and lines under the current state.
        Fuses GNN dynamic risk score predictions with structural betweenness centrality.
        """
        node_risk, edge_risk = self.risk_scores(x, edge_feats)
        
        # 1. Node analysis
        vuln_dict = self.analyzer.vulnerability_scores(node_risk)
        sorted_nodes = sorted(vuln_dict.items(), key=lambda item: item[1], reverse=True)
        critical_buses = [{"bus_id": int(n), "risk_score": float(s)} for n, s in sorted_nodes[:top_n]]
        
        # 2. Edge analysis
        edge_centrality = nx.edge_betweenness_centrality(self.analyzer.G)
        edge_risk_list = []
        for k, (u, v) in enumerate(self.edge_index):
            struct_centrality = edge_centrality.get((u, v), edge_centrality.get((v, u), 0.0))
            dyn_risk = float(edge_risk[k])
            fused_score = 0.4 * struct_centrality * 46 + 0.6 * dyn_risk
            
            edge_risk_list.append({
                "from": int(u),
                "to": int(v),
                "line_id": self.topo.lines[k]["id"],
                "risk_score": fused_score
            })
            
        critical_lines = sorted(edge_risk_list, key=lambda e: e["risk_score"], reverse=True)[:top_n]
        
        return critical_buses, critical_lines

    def propagation_prediction(self, source_bus, target_bus):
        """
        Computes shortest electrical propagation path between source and target buses.
        """
        return self.analyzer.propagation_paths(source_bus, target_bus)

# Singleton instance for production usage
_detector = None

def _get_detector():
    global _detector
    if _detector is None:
        _detector = GraphAnomalyDetector()
    return _detector

def classification(x, edge_feats=None):
    return _get_detector().classification(x, edge_feats)

def risk_scores(x, edge_feats=None):
    return _get_detector().risk_scores(x, edge_feats)

def critical_components(x, edge_feats=None, top_n=5):
    return _get_detector().critical_components(x, edge_feats, top_n)

def propagation_prediction(source_bus, target_bus):
    return _get_detector().propagation_prediction(source_bus, target_bus)
