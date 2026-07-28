import os
import sys
import json
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import TensorDataset, DataLoader

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))

from gnn_model import IEEE39GNN
from grid_topology import GridTopology
from gnn_evaluator import evaluate_gnn_performance

LABEL_MAP = {
    "NORMAL": 0,
    "N1_LINE": 1,
    "N1_GENERATOR": 2,
    "N2": 3,
    "VOLTAGE_INSTABILITY": 4,
    "FDIA": 5,
    "REPLAY": 6,
    "DOS": 7
}

def extract_network_parameters(topo: GridTopology):
    net = topo.net
    import pandapower as pp
    pp.runpp(net)
    ppc = net._ppc
    branch = ppc['branch']
    
    # Map internal to external bus indices
    ppc_bus_idx = ppc['bus'][:, 0].astype(int)
    
    num_edges = len(branch)
    edge_index = []
    
    r_arr = np.zeros(num_edges)
    x_arr = np.zeros(num_edges)
    b_arr = np.zeros(num_edges)
    tap_arr = np.zeros(num_edges)
    shift_arr = np.zeros(num_edges)
    f_bus_ext = np.zeros(num_edges, dtype=int)
    t_bus_ext = np.zeros(num_edges, dtype=int)
    
    is_trafo_arr = np.zeros(num_edges, dtype=bool)
    max_i_ka_arr = np.zeros(num_edges)
    sn_mva_arr = np.zeros(num_edges)
    vn_kv_arr = np.zeros(num_edges)
    
    adj_lists = {i: [] for i in range(39)}
    
    for k in range(num_edges):
        b_data = branch[k]
        f_bus_int = int(b_data[0])
        t_bus_int = int(b_data[1])
        
        ext_f = ppc_bus_idx[f_bus_int]
        ext_t = ppc_bus_idx[t_bus_int]
        
        edge_index.append((ext_f, ext_t))
        adj_lists[ext_f].append(k)
        adj_lists[ext_t].append(k)
        
        r_arr[k] = b_data[2]
        x_arr[k] = b_data[3]
        b_arr[k] = b_data[4]
        
        tap = b_data[8]
        if tap == 0.0:
            tap = 1.0
        tap_arr[k] = tap
        shift_arr[k] = np.radians(b_data[9])
        
        f_bus_ext[k] = ext_f
        t_bus_ext[k] = ext_t
        vn_kv_arr[k] = net.bus.vn_kv.at[ext_f]
        
        # Check if line or trafo
        lines = net.line[(net.line.from_bus == ext_f) & (net.line.to_bus == ext_t) | (net.line.from_bus == ext_t) & (net.line.to_bus == ext_f)]
        if len(lines) > 0:
            idx = lines.index[0]
            is_trafo_arr[k] = False
            max_i_ka_arr[k] = net.line.max_i_ka.at[idx]
            sn_mva_arr[k] = 1.0 # dummy
        else:
            trafos = net.trafo[(net.trafo.hv_bus == ext_f) & (net.trafo.lv_bus == ext_t) | (net.trafo.hv_bus == ext_t) & (net.trafo.lv_bus == ext_f)]
            if len(trafos) > 0:
                idx = trafos.index[0]
                is_trafo_arr[k] = True
                max_i_ka_arr[k] = 1.0 # dummy
                sn_mva_arr[k] = net.trafo.sn_mva.at[idx]
            else:
                is_trafo_arr[k] = False
                max_i_ka_arr[k] = 1.0
                sn_mva_arr[k] = 1.0
                
    params = {
        "r": r_arr,
        "x": x_arr,
        "b": b_arr,
        "tap": tap_arr,
        "shift": shift_arr,
        "f_bus": f_bus_ext,
        "t_bus": t_bus_ext,
        "vn_kv": vn_kv_arr,
        "is_trafo": is_trafo_arr,
        "max_i_ka": max_i_ka_arr,
        "sn_mva": sn_mva_arr,
        "adj_lists": adj_lists
    }
    return edge_index, params

def compute_vectorized_flows(V, theta, params):
    N = V.shape[0]
    num_edges = len(params["r"])
    
    f_bus = params["f_bus"]
    t_bus = params["t_bus"]
    
    V_f = V[:, f_bus]
    V_t = V[:, t_bus]
    theta_f = theta[:, f_bus]
    theta_t = theta[:, t_bus]
    
    V_f_c = V_f * np.exp(1j * theta_f)
    V_t_c = V_t * np.exp(1j * theta_t)
    
    r = params["r"]
    x = params["x"]
    b = params["b"]
    tap = params["tap"]
    shift = params["shift"]
    
    y = 1.0 / (r + 1j * x)
    
    I_from = ((y / tap**2) + 1j * b / 2) * V_f_c - (y / (tap * np.exp(1j * shift))) * V_t_c
    I_to = (y + 1j * b / 2) * V_t_c - (y / (tap * np.exp(-1j * shift))) * V_f_c
    
    S_from = V_f_c * np.conj(I_from) * 100.0
    S_to = V_t_c * np.conj(I_to) * 100.0
    
    P_flow = S_from.real / 100.0
    Q_flow = S_from.imag / 100.0
    
    i_base = 100.0 / (np.sqrt(3) * params["vn_kv"])
    i_from_ka = np.abs(I_from) * i_base
    i_to_ka = np.abs(I_to) * i_base
    i_ka = np.maximum(i_from_ka, i_to_ka)
    
    line_loading = (i_ka / params["max_i_ka"]) * 100.0
    s_max_mva = np.maximum(np.abs(S_from), np.abs(S_to))
    trafo_loading = (s_max_mva / params["sn_mva"]) * 100.0
    
    loading_percent = np.where(params["is_trafo"], trafo_loading, line_loading)
    loading_percent = np.clip(loading_percent, 0.0, 200.0)
    
    return P_flow, Q_flow, loading_percent

def train_gnn(dataset_path: str, device: str = "cpu"):
    print("=========================================")
    print("STARTING TOPOLOGY GNN TRAINING PIPELINE")
    print("=========================================")
    
    # 1. Load topology
    topo = GridTopology()
    edge_index, params = extract_network_parameters(topo)
    print(f"Graph loaded dynamically. Nodes (Buses): {topo.num_buses}, Edges (Lines/Trafos): {len(edge_index)}")
    
    # 2. Load dataset
    df = pd.read_csv(dataset_path)
    exclude_labels = ["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"]
    df_valid = df[~df["label"].isin(exclude_labels)].copy()
    print(f"Loaded valid samples: {len(df_valid)}")
    
    P_data = np.zeros((len(df_valid), 39))
    Q_data = np.zeros((len(df_valid), 39))
    V_data = np.zeros((len(df_valid), 39))
    theta_data = np.zeros((len(df_valid), 39))
    
    for i in range(1, 40):
        P_data[:, i-1] = df_valid[f"bus_{i}_P"].values / 100.0
        Q_data[:, i-1] = df_valid[f"bus_{i}_Q"].values / 100.0
        V_data[:, i-1] = df_valid[f"bus_{i}_V"].values
        theta_data[:, i-1] = df_valid[f"bus_{i}_theta"].values
        
    labels = df_valid["label"].map(LABEL_MAP).values.astype(np.int64)
    
    # 3. Compute edge features
    print("Computing vectorized edge features...")
    P_flow, Q_flow, loading_percent = compute_vectorized_flows(V_data, theta_data, params)
    
    N = len(df_valid)
    line_status = np.zeros((N, len(edge_index)))
    trafo_status = np.zeros((N, len(edge_index)))
    
    for k in range(len(edge_index)):
        if params["is_trafo"][k]:
            trafo_status[:, k] = 1.0
        else:
            line_status[:, k] = 1.0
            
    # 4. Tensors
    x_nodes = np.stack([P_data, Q_data, V_data, theta_data], axis=-1).astype(np.float32)
    x_edges = np.stack([P_flow, Q_flow, loading_percent / 100.0, line_status, trafo_status], axis=-1).astype(np.float32)
    
    # Risks
    node_risks = np.zeros((N, 39))
    edge_risks = np.zeros((N, len(edge_index)))
    
    for b in range(N):
        edge_risks[b, :] = np.clip(loading_percent[b, :] / 100.0, 0.0, 1.0)
        for i in range(39):
            v_dev = abs(V_data[b, i] - 1.0)
            adj_edges = params["adj_lists"][i]
            max_adj_load = np.max(loading_percent[b, adj_edges]) if len(adj_edges) > 0 else 0.0
            node_risks[b, i] = np.clip(5.0 * v_dev + 0.1 * (max_adj_load / 100.0), 0.0, 1.0)
            
    # 5. Split train / validation / test (70/15/15)
    np.random.seed(42)
    indices = np.random.permutation(N)
    
    train_end = int(0.70 * N)
    val_end = train_end + int(0.15 * N)
    
    train_idx = indices[:train_end]
    val_idx = indices[train_end:val_end]
    test_idx = indices[val_end:]
    
    X_node_train, X_edge_train, y_train, r_node_train, r_edge_train = x_nodes[train_idx], x_edges[train_idx], labels[train_idx], node_risks[train_idx], edge_risks[train_idx]
    X_node_val, X_edge_val, y_val, r_node_val, r_edge_val = x_nodes[val_idx], x_edges[val_idx], labels[val_idx], node_risks[val_idx], edge_risks[val_idx]
    X_node_test, X_edge_test, y_test, r_node_test, r_edge_test = x_nodes[test_idx], x_edges[test_idx], labels[test_idx], node_risks[test_idx], edge_risks[test_idx]
    
    # 6. Fit standardisation parameters on training set
    node_mean = X_node_train.mean(axis=(0, 1))
    node_std = X_node_train.std(axis=(0, 1))
    node_std[node_std < 1e-8] = 1.0
    
    edge_mean = X_edge_train.mean(axis=(0, 1))
    edge_std = X_edge_train.std(axis=(0, 1))
    edge_std[edge_std < 1e-8] = 1.0
    
    train_dataset = TensorDataset(
        torch.tensor(X_node_train), torch.tensor(X_edge_train), torch.tensor(y_train), 
        torch.tensor(r_node_train, dtype=torch.float32), torch.tensor(r_edge_train, dtype=torch.float32)
    )
    val_dataset = TensorDataset(
        torch.tensor(X_node_val), torch.tensor(X_edge_val), torch.tensor(y_val),
        torch.tensor(r_node_val, dtype=torch.float32), torch.tensor(r_edge_val, dtype=torch.float32)
    )
    test_dataset = TensorDataset(
        torch.tensor(X_node_test), torch.tensor(X_edge_test), torch.tensor(y_test),
        torch.tensor(r_node_test, dtype=torch.float32), torch.tensor(r_edge_test, dtype=torch.float32)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)
    
    # 7. Initialize model
    model = IEEE39GNN(edge_index=edge_index, hidden_dim=128, num_classes=8).to(device)
    model.node_mean.copy_(torch.tensor(node_mean, dtype=torch.float32).to(device))
    model.node_std.copy_(torch.tensor(node_std, dtype=torch.float32).to(device))
    model.edge_mean.copy_(torch.tensor(edge_mean, dtype=torch.float32).to(device))
    model.edge_std.copy_(torch.tensor(edge_std, dtype=torch.float32).to(device))
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002, weight_decay=1e-5)
    class_criterion = nn.CrossEntropyLoss()
    risk_criterion = nn.MSELoss()
    
    epochs = 35
    history = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": []
    }
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for batch_xn, batch_xe, batch_y, batch_rn, batch_re in train_loader:
            batch_xn = batch_xn.to(device)
            batch_xe = batch_xe.to(device)
            batch_y = batch_y.to(device)
            batch_rn = batch_rn.to(device)
            batch_re = batch_re.to(device)
            
            optimizer.zero_grad()
            logits, pred_rn, pred_re = model(batch_xn, batch_xe)
            
            loss_cls = class_criterion(logits, batch_y)
            loss_rn = risk_criterion(pred_rn, batch_rn)
            loss_re = risk_criterion(pred_re, batch_re)
            
            # Focused classification loss weighting:
            loss = loss_cls + 1.0 * loss_rn + 1.0 * loss_re
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * batch_xn.size(0)
            preds = torch.argmax(logits, dim=-1)
            correct += (preds == batch_y).sum().item()
            total += batch_xn.size(0)
            
        train_loss = total_loss / len(train_idx)
        train_acc = correct / total
        
        # Validation Pass
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch_xn, batch_xe, batch_y, batch_rn, batch_re in val_loader:
                batch_xn = batch_xn.to(device)
                batch_xe = batch_xe.to(device)
                batch_y = batch_y.to(device)
                batch_rn = batch_rn.to(device)
                batch_re = batch_re.to(device)
                
                logits, pred_rn, pred_re = model(batch_xn, batch_xe)
                loss_cls = class_criterion(logits, batch_y)
                loss_rn = risk_criterion(pred_rn, batch_rn)
                loss_re = risk_criterion(pred_re, batch_re)
                
                loss = loss_cls + 1.0 * loss_rn + 1.0 * loss_re
                val_loss += loss.item() * batch_xn.size(0)
                
                preds = torch.argmax(logits, dim=-1)
                val_correct += (preds == batch_y).sum().item()
                val_total += batch_xn.size(0)
                
        val_loss = val_loss / len(val_idx)
        val_acc = val_correct / val_total
        
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%")
            
    # Save trained model weights
    model_save_path = os.path.join(current_dir, "trained_gnn_model.pt")
    torch.save(model.state_dict(), model_save_path)
    print(f"Model saved to: {model_save_path}")
    
    # Save training metrics
    metrics_save_path = os.path.join(current_dir, "training_metrics.json")
    with open(metrics_save_path, "w") as f:
        json.dump(history, f, indent=4)
    print(f"Training metrics saved to: {metrics_save_path}")
    
    # Save evaluation results
    print("\nRunning final test set evaluation...")
    eval_results = evaluate_gnn_performance(model, test_loader, device=device)
    
    eval_save_path = os.path.join(current_dir, "evaluation_results.json")
    with open(eval_save_path, "w") as f:
        json.dump(eval_results, f, indent=4)
    print(f"Evaluation results saved to: {eval_save_path}")
    
    return model, edge_index, params

if __name__ == "__main__":
    dataset_path = os.path.join(parent_dir, "data_collector", "data", "ieee39_telemetry_dataset.csv")
    train_gnn(dataset_path)
