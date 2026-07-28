import os
import sys
import torch
import numpy as np
import json
from typing import Dict, Any, Tuple

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from physics_loss import IEEE39PhysicsLoss


def compute_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return float(1.0 - ss_res / ss_tot)

def evaluate_pinn(model: torch.nn.Module, test_loader: torch.utils.data.DataLoader, 
                  physics_loss_fn: IEEE39PhysicsLoss, device: str = "cpu") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Evaluates the trained PINN model on the test dataset.
    Computes MAE, RMSE, R2, and Physics Constraint Violation Rate.
    """
    model.eval()
    
    all_true = []
    all_pred = []
    
    total_violations = 0
    total_samples = 0
    
    physics_losses = []
    
    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            reconstructed, pred_P, pred_Q, pred_V, pred_theta = model(batch)
            
            # Split ground truth
            true_P = batch[:, 0:39]
            true_Q = batch[:, 39:78]
            true_V = batch[:, 78:117]
            true_theta = batch[:, 117:156]
            
            # Compute physics loss
            loss_phys, breakdown = physics_loss_fn(pred_P, pred_Q, pred_V, pred_theta)
            physics_losses.append(loss_phys.item())
            
            # Convert to numpy
            np_true_P = true_P.cpu().numpy()
            np_true_Q = true_Q.cpu().numpy()
            np_true_V = true_V.cpu().numpy()
            np_true_theta = true_theta.cpu().numpy()
            
            np_pred_P = pred_P.cpu().numpy()
            np_pred_Q = pred_Q.cpu().numpy()
            np_pred_V = pred_V.cpu().numpy()
            np_pred_theta = pred_theta.cpu().numpy()
            
            all_true.append(batch.cpu().numpy())
            all_pred.append(reconstructed.cpu().numpy())
            
            # Audit physics violations for each sample in the batch
            batch_size = batch.shape[0]
            for i in range(batch_size):
                total_samples += 1
                violated = False
                
                # Check V bounds: [0.85, 1.15]
                v_sample = np_pred_V[i]
                if np.any(v_sample < 0.85) or np.any(v_sample > 1.15):
                    violated = True
                    
                # Check theta bounds: [-pi, pi]
                theta_sample = np_pred_theta[i]
                if np.any(theta_sample < -np.pi) or np.any(theta_sample > np.pi):
                    violated = True
                    
                # Check power balance mismatch
                # S = V I*
                V_c = np_pred_V[i] * (np.cos(np_pred_theta[i]) + 1j * np.sin(np_pred_theta[i]))
                I_c = physics_loss_fn.Y_bus @ V_c
                S_c = V_c * np.conj(I_c)
                
                P_calc = np.real(S_c)
                Q_calc = np.imag(S_c)
                
                P_pred_pu = np_pred_P[i] / 100.0
                Q_pred_pu = np_pred_Q[i] / 100.0
                
                # Threshold of 0.05 pu (5 MW / 5 Mvar) average nodal mismatch
                mae_P = np.mean(np.abs(P_pred_pu + P_calc))
                mae_Q = np.mean(np.abs(Q_pred_pu + Q_calc))
                if mae_P > 0.05 or mae_Q > 0.05:
                    violated = True
                    
                if violated:
                    total_violations += 1
                    
    # Concatenate all batches
    np_all_true = np.vstack(all_true)
    np_all_pred = np.vstack(all_pred)
    
    true_P_all = np_all_true[:, 0:39]
    true_Q_all = np_all_true[:, 39:78]
    true_V_all = np_all_true[:, 78:117]
    true_theta_all = np_all_true[:, 117:156]
    
    pred_P_all = np_all_pred[:, 0:39]
    pred_Q_all = np_all_pred[:, 39:78]
    pred_V_all = np_all_pred[:, 78:117]
    pred_theta_all = np_all_pred[:, 117:156]
    
    # Calculate evaluation metrics per variable type
    metrics = {}
    for name, t_val, p_val in [("P", true_P_all, pred_P_all), 
                               ("Q", true_Q_all, pred_Q_all), 
                               ("V", true_V_all, pred_V_all), 
                               ("theta", true_theta_all, pred_theta_all)]:
        mae = float(np.mean(np.abs(t_val - p_val)))
        rmse = float(np.sqrt(np.mean((t_val - p_val) ** 2)))
        r2 = compute_r2(t_val, p_val)
        
        metrics[name] = {
            "MAE": round(mae, 5),
            "RMSE": round(rmse, 5),
            "R2": round(r2, 5)
        }
        
    violation_rate = float(total_violations / total_samples)
    
    validation_results = {
        "metrics": metrics,
        "physics_metrics": {
            "violation_rate": round(violation_rate, 5),
            "mean_physics_loss": round(float(np.mean(physics_losses)), 6)
        }
    }
    
    print("\n=========================================")
    print("PINN MODEL EVALUATION COMPLETE")
    print("=========================================")
    print(f"Test Samples Audited    : {total_samples}")
    print(f"Physics Violations      : {total_violations}")
    print(f"Violation Rate          : {violation_rate*100:.2f}%")
    print(f"Mean Physics Loss       : {np.mean(physics_losses):.6f}")
    print("-" * 40)
    for var, vals in metrics.items():
        print(f"{var:<6} -> MAE: {vals['MAE']:<8.4f} | RMSE: {vals['RMSE']:<8.4f} | R²: {vals['R2']:<8.4f}")
    print("=========================================\n")
    
    return metrics, validation_results
