import os
import sys
import json
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))

from stgnn_model import IEEE39STGNN
from grid_topology import GridTopology
from gnn_trainer import extract_network_parameters, compute_vectorized_flows
from stgnn_evaluator import evaluate_stgnn_performance

def create_temporal_sequences(x_nodes, x_edges, node_risks, edge_risks, seq_len=20, future_horizon=5):
    """
    Creates overlapping sequences.
    For each time step t, returns:
      - x_node_seq: sequence from t-seq_len+1 to t
      - x_edge_seq: sequence from t-seq_len+1 to t
      - target_node_risk: node risk at t + future_horizon
      - target_edge_risk: edge risk at t + future_horizon
      - baseline_node_risk: node risk at t (for naive baseline)
      - baseline_edge_risk: edge risk at t (for naive baseline)
    """
    N = len(x_nodes)
    X_n = []
    X_e = []
    y_n = []
    y_e = []
    base_n = []
    base_e = []
    
    for i in range(seq_len - 1, N - future_horizon):
        X_n.append(x_nodes[i - seq_len + 1 : i + 1])
        X_e.append(x_edges[i - seq_len + 1 : i + 1])
        y_n.append(node_risks[i + future_horizon])
        y_e.append(edge_risks[i + future_horizon])
        base_n.append(node_risks[i])
        base_e.append(edge_risks[i])
        
    return (np.array(X_n, dtype=np.float32), 
            np.array(X_e, dtype=np.float32), 
            np.array(y_n, dtype=np.float32), 
            np.array(y_e, dtype=np.float32),
            np.array(base_n, dtype=np.float32),
            np.array(base_e, dtype=np.float32))

def train_stgnn(dataset_path: str, device: str = "cpu"):
    print("=========================================")
    print("STARTING SPATIO-TEMPORAL GNN TRAINING")
    print("=========================================")
    
    # 1. Load topology parameters
    topo = GridTopology()
    edge_index, params = extract_network_parameters(topo)
    print(f"Topology loaded dynamically. Buses: {topo.num_buses}, Edges: {len(edge_index)}")
    
    # 2. Load dataset
    df = pd.read_csv(dataset_path)
    exclude_labels = ["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"]
    df_valid = df[~df["label"].isin(exclude_labels)].copy()
    print(f"Loaded valid chronological samples: {len(df_valid)}")
    
    P_data = np.zeros((len(df_valid), 39))
    Q_data = np.zeros((len(df_valid), 39))
    V_data = np.zeros((len(df_valid), 39))
    theta_data = np.zeros((len(df_valid), 39))
    
    for i in range(1, 40):
        P_data[:, i-1] = df_valid[f"bus_{i}_P"].values / 100.0
        Q_data[:, i-1] = df_valid[f"bus_{i}_Q"].values / 100.0
        V_data[:, i-1] = df_valid[f"bus_{i}_V"].values
        theta_data[:, i-1] = df_valid[f"bus_{i}_theta"].values
        
    # 3. Compute edge features algebraically
    P_flow, Q_flow, loading_percent = compute_vectorized_flows(V_data, theta_data, params)
    
    N = len(df_valid)
    line_status = np.zeros((N, len(edge_index)))
    trafo_status = np.zeros((N, len(edge_index)))
    for k in range(len(edge_index)):
        if params["is_trafo"][k]:
            trafo_status[:, k] = 1.0
        else:
            line_status[:, k] = 1.0
            
    # Node features: (N, 39, 4)
    x_nodes = np.stack([P_data, Q_data, V_data, theta_data], axis=-1).astype(np.float32)
    # Edge features: (N, 46, 5)
    x_edges = np.stack([P_flow, Q_flow, loading_percent / 100.0, line_status, trafo_status], axis=-1).astype(np.float32)
    
    # Calculate snapshot-wise node and edge risk scores (as used in v9.5)
    node_risks = np.zeros((N, 39))
    edge_risks = np.zeros((N, len(edge_index)))
    for b in range(N):
        edge_risks[b, :] = np.clip(loading_percent[b, :] / 100.0, 0.0, 1.0)
        for i in range(39):
            v_dev = abs(V_data[b, i] - 1.0)
            adj_edges = params["adj_lists"][i]
            max_adj_load = np.max(loading_percent[b, adj_edges]) if len(adj_edges) > 0 else 0.0
            node_risks[b, i] = np.clip(5.0 * v_dev + 0.1 * (max_adj_load / 100.0), 0.0, 1.0)
            
    # 4. Create sequences (20-step input window, 5-step future prediction target)
    print("Creating sliding window sequences...")
    X_node_all, X_edge_all, y_node_all, y_edge_all, base_node_all, base_edge_all = create_temporal_sequences(
        x_nodes, x_edges, node_risks, edge_risks, seq_len=20, future_horizon=5
    )
    n_sequences = len(X_node_all)
    print(f"Total sequences generated: {n_sequences}")
    
    # 5. Split train / validation / test (70/15/15)
    np.random.seed(42)
    indices = np.random.permutation(n_sequences)
    
    train_end = int(0.70 * n_sequences)
    val_end = train_end + int(0.15 * n_sequences)
    
    train_idx = indices[:train_end]
    val_idx = indices[train_end:val_end]
    test_idx = indices[val_end:]
    
    # Slice datasets
    Xn_train, Xe_train, yn_train, ye_train = X_node_all[train_idx], X_edge_all[train_idx], y_node_all[train_idx], y_edge_all[train_idx]
    Xn_val, Xe_val, yn_val, ye_val = X_node_all[val_idx], X_edge_all[val_idx], y_node_all[val_idx], y_edge_all[val_idx]
    Xn_test, Xe_test, yn_test, ye_test, bn_test, be_test = X_node_all[test_idx], X_edge_all[test_idx], y_node_all[test_idx], y_edge_all[test_idx], base_node_all[test_idx], base_edge_all[test_idx]
    
    # Fit standardisation parameters on training features
    node_mean = Xn_train.mean(axis=(0, 1, 2))
    node_std = Xn_train.std(axis=(0, 1, 2))
    node_std[node_std < 1e-8] = 1.0
    
    edge_mean = Xe_train.mean(axis=(0, 1, 2))
    edge_std = Xe_train.std(axis=(0, 1, 2))
    edge_std[edge_std < 1e-8] = 1.0
    
    # Create DataLoaders
    train_dataset = TensorDataset(torch.tensor(Xn_train), torch.tensor(Xe_train), torch.tensor(yn_train), torch.tensor(ye_train))
    val_dataset = TensorDataset(torch.tensor(Xn_val), torch.tensor(Xe_val), torch.tensor(yn_val), torch.tensor(ye_val))
    test_dataset = TensorDataset(
        torch.tensor(Xn_test), torch.tensor(Xe_test), 
        torch.tensor(yn_test), torch.tensor(ye_test),
        torch.tensor(bn_test), torch.tensor(be_test)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)
    
    # 6. Initialize model
    model = IEEE39STGNN(edge_index=edge_index, hidden_dim=64).to(device)
    model.node_mean.copy_(torch.tensor(node_mean, dtype=torch.float32).to(device))
    model.node_std.copy_(torch.tensor(node_std, dtype=torch.float32).to(device))
    model.edge_mean.copy_(torch.tensor(edge_mean, dtype=torch.float32).to(device))
    model.edge_std.copy_(torch.tensor(edge_std, dtype=torch.float32).to(device))
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002, weight_decay=1e-5)
    criterion = nn.MSELoss()
    
    # 7. Training Loop
    epochs = 20
    history = {
        "train_loss": [],
        "val_loss": [],
        "train_node_mse": [],
        "train_edge_mse": [],
        "val_node_mse": [],
        "val_edge_mse": []
    }
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        node_mse_total = 0.0
        edge_mse_total = 0.0
        
        for batch_xn, batch_xe, batch_yn, batch_ye in train_loader:
            batch_xn = batch_xn.to(device)
            batch_xe = batch_xe.to(device)
            batch_yn = batch_yn.to(device)
            batch_ye = batch_ye.to(device)
            
            optimizer.zero_grad()
            pred_yn, pred_ye = model(batch_xn, batch_xe)
            
            loss_n = criterion(pred_yn, batch_yn)
            loss_e = criterion(pred_ye, batch_ye)
            loss = loss_n + loss_e
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * batch_xn.size(0)
            node_mse_total += loss_n.item() * batch_xn.size(0)
            edge_mse_total += loss_e.item() * batch_xn.size(0)
            
        train_loss = total_loss / len(Xn_train)
        train_node_mse = node_mse_total / len(Xn_train)
        train_edge_mse = edge_mse_total / len(Xn_train)
        
        # Validation Pass
        model.eval()
        val_loss_total = 0.0
        val_node_mse_total = 0.0
        val_edge_mse_total = 0.0
        
        with torch.no_grad():
            for batch_xn, batch_xe, batch_yn, batch_ye in val_loader:
                batch_xn = batch_xn.to(device)
                batch_xe = batch_xe.to(device)
                batch_yn = batch_yn.to(device)
                batch_ye = batch_ye.to(device)
                
                pred_yn, pred_ye = model(batch_xn, batch_xe)
                loss_n = criterion(pred_yn, batch_yn)
                loss_e = criterion(pred_ye, batch_ye)
                
                val_loss_total += (loss_n.item() + loss_e.item()) * batch_xn.size(0)
                val_node_mse_total += loss_n.item() * batch_xn.size(0)
                val_edge_mse_total += loss_e.item() * batch_xn.size(0)
                
        val_loss = val_loss_total / len(Xn_val)
        val_node_mse = val_node_mse_total / len(Xn_val)
        val_edge_mse = val_edge_mse_total / len(Xn_val)
        
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_node_mse"].append(train_node_mse)
        history["train_edge_mse"].append(train_edge_mse)
        history["val_node_mse"].append(val_node_mse)
        history["val_edge_mse"].append(val_edge_mse)
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.5f} Node MSE: {train_node_mse:.5f} | Val Loss: {val_loss:.5f} Node MSE: {val_node_mse:.5f}")
            
    # Serialize model weights
    model_save_path = os.path.join(current_dir, "trained_stgnn_model.pt")
    torch.save(model.state_dict(), model_save_path)
    print(f"Model saved to: {model_save_path}")
    
    # Save training metrics
    metrics_save_path = os.path.join(current_dir, "stgnn_training_metrics.json")
    with open(metrics_save_path, "w") as f:
        json.dump(history, f, indent=4)
    print(f"Training metrics saved to: {metrics_save_path}")
    
    # Evaluate on Test Set
    print("\nRunning final ST-GNN test evaluation...")
    eval_results = evaluate_stgnn_performance(model, test_loader, device=device)
    
    eval_save_path = os.path.join(current_dir, "stgnn_evaluation_results.json")
    with open(eval_save_path, "w") as f:
        json.dump(eval_results, f, indent=4)
    print(f"Evaluation results saved to: {eval_save_path}")
    
    return model, edge_index, params

if __name__ == "__main__":
    dataset_path = os.path.join(parent_dir, "data_collector", "data", "ieee39_telemetry_dataset.csv")
    train_stgnn(dataset_path)
