import torch
import torch.nn as nn

# IEEE 9-bus Line reactance values
X_LINE = torch.tensor([0.0576, 0.0625, 0.0586, 0.085, 0.092, 0.161, 0.072, 0.161, 0.1008], dtype=torch.float32)

# Line connections (from, to) 0-indexed:
LINE_CONNECTIONS = [
    (0, 3), # L1_4
    (1, 6), # L2_7
    (2, 8), # L3_9
    (3, 4), # L4_5
    (3, 8), # L4_9
    (4, 5), # L5_6
    (5, 6), # L6_7
    (6, 7), # L7_8
    (7, 8)  # L8_9
]

# Incidence Matrix C (9 buses, 9 lines)
C_MATRIX = torch.zeros(9, 9, dtype=torch.float32)
for k, (f, t) in enumerate(LINE_CONNECTIONS):
    C_MATRIX[f, k] = 1.0
    C_MATRIX[t, k] = -1.0

# Adjacency connection degrees per bus for topology-aware KCL weighting
BUS_DEGREES = torch.tensor([1.0, 1.0, 1.0, 3.0, 2.0, 2.0, 2.0, 2.0, 2.0], dtype=torch.float32)

def compute_pinn_loss(y_pred, y_true, 
                       alpha_supervised=1.0, 
                       alpha_kcl=0.1, 
                       alpha_kvl=0.1, 
                       alpha_topo=0.1, 
                       alpha_stability=0.05,
                       alpha_dc_flow=0.1,
                       alpha_trust=0.05,
                       alpha_limit=0.05):
    """
    Computes a joint supervised, NLL uncertainty, and physics-informed loss for the mature PINN grid predictor.
    
    y_pred: (batch, 38) -> predicted:
            - voltages V: cols 0-8
            - voltage angles theta: cols 9-17
            - active flows P (p.u.): cols 18-26
            - reactive flows Q (p.u.): cols 27-35
            - cyber logit: col 36
            - predictive uncertainty logit (log-variance s): col 37
            
    y_true: (batch, 83) -> true:
            - voltages: cols 0-8
            - voltage angles: cols 9-17
            - active power injections (MW): cols 18-26 -> divide by 100.0 to get p.u.
            - reactive power injections (MVar): cols 27-35 -> divide by 100.0 to get p.u.
            - active flows P (MW): cols 36-44 -> divide by 100.0 to get p.u.
            - reactive flows Q (MVar): cols 45-53 -> divide by 100.0 to get p.u.
            - breaker states: cols 63-71
            - cyber instability label: col 82
    """
    batch_size = y_pred.shape[0]
    device = y_pred.device
    
    C = C_MATRIX.to(device)
    X_line = X_LINE.to(device)
    degrees = BUS_DEGREES.to(device)
    
    # 1. Extract Preds
    pred_V = y_pred[:, 0:9]
    pred_angle = y_pred[:, 9:18]
    pred_P = y_pred[:, 18:27]
    pred_Q = y_pred[:, 27:35] # Note: Q is cols 27-35 (9 values)
    # Wait, col 35 is index 35. 27 to 35 inclusive is 9 values: 27, 28, 29, 30, 31, 32, 33, 34, 35.
    pred_Q = y_pred[:, 27:36] # cols 27-35
    pred_cyber = y_pred[:, 36]
    pred_logvar = y_pred[:, 37]
    
    # 2. Extract Trues
    true_V = y_true[:, 0:9]
    true_angle = y_true[:, 9:18]
    true_inj_P = y_true[:, 18:27] / 100.0
    true_inj_Q = y_true[:, 27:36] / 100.0
    true_flow_P = y_true[:, 36:45] / 100.0
    true_flow_Q = y_true[:, 45:54] / 100.0
    true_breakers = y_true[:, 63:72]
    true_cyber = y_true[:, 82]
    
    # --- SUPERVISED & NLL LOSS ---
    loss_V = nn.MSELoss()(pred_V, true_V)
    loss_angle = nn.MSELoss()(pred_angle, true_angle)
    loss_flow_P = nn.MSELoss()(pred_P, true_flow_P)
    loss_flow_Q = nn.MSELoss()(pred_Q, true_flow_Q)
    loss_cyber = nn.BCEWithLogitsLoss()(pred_cyber, true_cyber)
    
    # Gaussian Negative Log-Likelihood for learned uncertainty
    # pred_logvar represents log(sigma^2) of prediction error
    loss_nll = 0.5 * torch.mean(torch.exp(-pred_logvar) * torch.mean((pred_V - true_V)**2, dim=1) + pred_logvar)
    
    loss_supervised = loss_V + loss_angle + loss_flow_P + loss_flow_Q + loss_cyber + loss_nll
    
    # --- PHYSICS LOSSES ---
    masked_P = pred_P * true_breakers
    masked_Q = pred_Q * true_breakers
    
    # A. Topology-Aware KCL Power Balance (Weighted by Bus degrees)
    flow_leaving_P = torch.matmul(C, masked_P.t()).t()
    flow_leaving_Q = torch.matmul(C, masked_Q.t()).t()
    
    kcl_mismatch_P = true_inj_P - flow_leaving_P
    kcl_mismatch_Q = true_inj_Q - flow_leaving_Q
    
    loss_kcl = torch.mean(degrees * (kcl_mismatch_P**2 + kcl_mismatch_Q**2))
    
    # B. Dynamic Capacity-Weighted KVL Voltage Drop
    # Lines with higher load have higher weights to focus prediction on cascading nodes
    line_loads = true_flow_P**2 + true_flow_Q**2
    line_weights = 1.0 + 2.0 * torch.clamp(line_loads, max=2.0)
    
    kvl_errors = []
    for k, (f, t) in enumerate(LINE_CONNECTIONS):
        V_from = pred_V[:, f]
        V_to = pred_V[:, t]
        Q_k = pred_Q[:, k]
        X_k = X_line[k]
        breaker_k = true_breakers[:, k]
        
        v_drop = V_from - V_to
        kvl_err = breaker_k * (v_drop - Q_k * X_k)
        kvl_errors.append(kvl_err.unsqueeze(1))
        
    kvl_errors_tensor = torch.cat(kvl_errors, dim=1)
    loss_kvl = torch.mean(line_weights * (kvl_errors_tensor**2))
    
    # C. Differentiable DC Power Flow (P_line = delta_theta / X)
    dc_flow_errors = []
    for k, (f, t) in enumerate(LINE_CONNECTIONS):
        theta_from = pred_angle[:, f]
        theta_to = pred_angle[:, t]
        P_k = pred_P[:, k]
        X_k = X_line[k]
        breaker_k = true_breakers[:, k]
        
        expected_flow = (theta_from - theta_to) / X_k
        err = breaker_k * (P_k - expected_flow)
        dc_flow_errors.append(err.unsqueeze(1))
        
    dc_flow_errors_tensor = torch.cat(dc_flow_errors, dim=1)
    loss_dc_flow = torch.mean(line_weights * (dc_flow_errors_tensor**2))
    
    # D. Attack-Aware Topology open-breaker flow penalty
    # Scale topological constraint weights up to 3x under active cyber attacks
    attack_weight = 1.0 + 2.0 * true_cyber.unsqueeze(1)
    topo_err_P = (1.0 - true_breakers) * pred_P
    topo_err_Q = (1.0 - true_breakers) * pred_Q
    loss_topo = torch.mean(attack_weight * (topo_err_P**2 + topo_err_Q**2))
    
    # E. Attack-Aware Stability range violation penalty
    stability_err_low = torch.clamp(0.95 - pred_V, min=0.0)
    stability_err_high = torch.clamp(pred_V - 1.05, min=0.0)
    loss_stability = torch.mean(attack_weight * (stability_err_low**2 + stability_err_high**2))
    
    # F. Simulated Trust Consistency Loss
    # Train predictor to align closely with telemetry unless cyber intrusion is active on that node
    fdia_active = y_true[:, 77] if y_true.shape[1] > 77 else torch.zeros(batch_size, device=device)
    trust_V = torch.ones((batch_size, 9), device=device)
    # Bus 5 (index 4) trust is degraded under FDIA simulation
    trust_V[:, 4] = 1.0 - 0.9 * fdia_active
    loss_trust_cons = torch.mean(trust_V * (pred_V - true_V)**2)
    
    # G. Voltage Limit Penalty & Line Loading Penalty
    loss_volt_limit = torch.mean(torch.clamp(0.90 - pred_V, min=0.0)**2 + torch.clamp(pred_V - 1.10, min=0.0)**2)
    loss_line_loading = torch.mean(torch.clamp(line_flows_sq := (pred_P**2 + pred_Q**2) - 1.2, min=0.0))
    
    # Adaptive Penalty Weighting / Dynamic Constraint Balancing
    # Adjust KCL and KVL/DC-flow loss ratios dynamically to match supervised loss magnitude
    with torch.no_grad():
        sup_val = float(loss_supervised.item())
        kcl_val = float(loss_kcl.item())
        kvl_val = float(loss_kvl.item())
        dc_val = float(loss_dc_flow.item())
        
        w_kcl = max(0.01, min(1.0, (sup_val / (kcl_val + 1e-6)) * 0.1))
        w_kvl = max(0.01, min(1.0, (sup_val / (kvl_val + 1e-6)) * 0.1))
        w_dc = max(0.01, min(1.0, (sup_val / (dc_val + 1e-6)) * 0.1))
        
    # Combined Loss
    total_loss = (alpha_supervised * loss_supervised + 
                  w_kcl * alpha_kcl * loss_kcl + 
                  w_kvl * alpha_kvl * loss_kvl + 
                  w_dc * alpha_dc_flow * loss_dc_flow + 
                  alpha_topo * loss_topo + 
                  alpha_stability * loss_stability +
                  alpha_trust * loss_trust_cons +
                  alpha_limit * (loss_volt_limit + loss_line_loading))
                  
    return total_loss, {
        "loss_supervised": loss_supervised.item(),
        "loss_V": loss_V.item(),
        "loss_angle": loss_angle.item(),
        "loss_flow_P": loss_flow_P.item(),
        "loss_flow_Q": loss_flow_Q.item(),
        "loss_cyber": loss_cyber.item(),
        "loss_nll": loss_nll.item(),
        "loss_kcl": loss_kcl.item(),
        "loss_kvl": loss_kvl.item(),
        "loss_dc_flow": loss_dc_flow.item(),
        "loss_topo": loss_topo.item(),
        "loss_stability": loss_stability.item(),
        "loss_trust_cons": loss_trust_cons.item(),
        "loss_volt_limit": loss_volt_limit.item(),
        "loss_line_loading": loss_line_loading.item(),
        "total_loss": total_loss.item()
    }
