import torch
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def evaluate_stgnn_performance(model, data_loader, device="cpu"):
    """
    Evaluates the ST-GNN model predictions on the test loader and compares them
    against a naive baseline (which assumes risk remains unchanged).
    """
    model.eval()
    
    all_targets_node = []
    all_targets_edge = []
    all_preds_node = []
    all_preds_edge = []
    all_baselines_node = []
    all_baselines_edge = []
    
    with torch.no_grad():
        for batch_xn, batch_xe, batch_yn, batch_ye, batch_bn, batch_be in data_loader:
            batch_xn = batch_xn.to(device)
            batch_xe = batch_xe.to(device)
            
            # ST-GNN predictions
            pred_yn, pred_ye = model(batch_xn, batch_xe)
            
            all_targets_node.extend(batch_yn.numpy())
            all_targets_edge.extend(batch_ye.numpy())
            all_preds_node.extend(pred_yn.cpu().numpy())
            all_preds_edge.extend(pred_ye.cpu().numpy())
            
            # Naive baseline values (current risk at time t)
            all_baselines_node.extend(batch_bn.numpy())
            all_baselines_edge.extend(batch_be.numpy())
            
    all_targets_node = np.array(all_targets_node)
    all_targets_edge = np.array(all_targets_edge)
    all_preds_node = np.array(all_preds_node)
    all_preds_edge = np.array(all_preds_edge)
    all_baselines_node = np.array(all_baselines_node)
    all_baselines_edge = np.array(all_baselines_edge)
    
    # 1. Compute ST-GNN Metrics
    node_rmse = np.sqrt(mean_squared_error(all_targets_node, all_preds_node))
    node_mae = mean_absolute_error(all_targets_node, all_preds_node)
    node_r2 = r2_score(all_targets_node, all_preds_node)
    
    edge_rmse = np.sqrt(mean_squared_error(all_targets_edge, all_preds_edge))
    edge_mae = mean_absolute_error(all_targets_edge, all_preds_edge)
    edge_r2 = r2_score(all_targets_edge, all_preds_edge)
    
    # 2. Compute Naive Baseline Metrics (state at t predicting state at t+5)
    base_node_rmse = np.sqrt(mean_squared_error(all_targets_node, all_baselines_node))
    base_node_mae = mean_absolute_error(all_targets_node, all_baselines_node)
    base_node_r2 = r2_score(all_targets_node, all_baselines_node)
    
    base_edge_rmse = np.sqrt(mean_squared_error(all_targets_edge, all_baselines_edge))
    base_edge_mae = mean_absolute_error(all_targets_edge, all_baselines_edge)
    base_edge_r2 = r2_score(all_targets_edge, all_baselines_edge)
    
    results = {
        "stgnn": {
            "node": {
                "rmse": float(node_rmse),
                "mae": float(node_mae),
                "r2": float(node_r2)
            },
            "edge": {
                "rmse": float(edge_rmse),
                "mae": float(edge_mae),
                "r2": float(edge_r2)
            }
        },
        "baseline": {
            "node": {
                "rmse": float(base_node_rmse),
                "mae": float(base_node_mae),
                "r2": float(base_node_r2)
            },
            "edge": {
                "rmse": float(base_edge_rmse),
                "mae": float(base_edge_mae),
                "r2": float(base_edge_r2)
            }
        },
        "comparison": {
            "node_rmse_reduction_pct": float((base_node_rmse - node_rmse) / base_node_rmse * 100.0),
            "edge_rmse_reduction_pct": float((base_edge_rmse - edge_rmse) / base_edge_rmse * 100.0)
        }
    }
    
    print("\n=========================================")
    print("ST-GNN EVALUATION RESULTS VS NAIVE BASELINE")
    print("=========================================")
    print("Node Risk Forecast (t+5):")
    print(f"  ST-GNN   - RMSE: {node_rmse:.5f} | MAE: {node_mae:.5f} | R2: {node_r2:.4f}")
    print(f"  Baseline - RMSE: {base_node_rmse:.5f} | MAE: {base_node_mae:.5f} | R2: {base_node_r2:.4f}")
    print(f"  RMSE Reduction: {results['comparison']['node_rmse_reduction_pct']:.2f}%")
    print("Edge Risk Forecast (t+5):")
    print(f"  ST-GNN   - RMSE: {edge_rmse:.5f} | MAE: {edge_mae:.5f} | R2: {edge_r2:.4f}")
    print(f"  Baseline - RMSE: {base_edge_rmse:.5f} | MAE: {base_edge_mae:.5f} | R2: {base_edge_r2:.4f}")
    print(f"  RMSE Reduction: {results['comparison']['edge_rmse_reduction_pct']:.2f}%")
    print("=========================================")
    
    return results
