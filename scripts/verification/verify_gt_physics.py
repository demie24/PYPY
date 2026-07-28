import os
import sys
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "digital_twin"))

from pinn_trainer import train_val_test_split
from physics_loss import IEEE39PhysicsLoss

def verify_gt_physics(dataset_path: str):
    print("=========================================")
    # 1. Load data
    df = pd.read_csv(dataset_path)
    df_valid = df[~df["label"].isin(["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"])].copy()
    
    p_cols = [f"bus_{i}_P" for i in range(1, 40)]
    q_cols = [f"bus_{i}_Q" for i in range(1, 40)]
    v_cols = [f"bus_{i}_V" for i in range(1, 40)]
    theta_cols = [f"bus_{i}_theta" for i in range(1, 40)]
    feature_cols = p_cols + q_cols + v_cols + theta_cols
    
    data_all = df_valid[feature_cols].values.astype(np.float32)
    _, _, test_data = train_val_test_split(data_all)
    
    # 2. Get corrected Ybus from physics loss
    physics_loss_fn = IEEE39PhysicsLoss(device="cpu")
    Ybus = physics_loss_fn.Y_bus
    
    # 3. Evaluate mismatch over test set
    mis_P_all = []
    mis_Q_all = []
    
    for i in range(len(test_data)):
        true_P = test_data[i, 0:39]
        true_Q = test_data[i, 39:78]
        true_V = test_data[i, 78:117]
        true_theta = test_data[i, 117:156]
        
        V_c = true_V * (np.cos(true_theta) + 1j * np.sin(true_theta))
        I_c = Ybus @ V_c
        S_c = V_c * np.conj(I_c)
        
        P_calc = np.real(S_c)
        Q_calc = np.imag(S_c)
        
        P_true_pu = true_P / 100.0
        Q_true_pu = true_Q / 100.0
        
        mis_P_all.append(np.abs(P_true_pu + P_calc))
        mis_Q_all.append(np.abs(Q_true_pu + Q_calc))
        
    mis_P_all = np.array(mis_P_all).flatten()
    mis_Q_all = np.array(mis_Q_all).flatten()
    
    print("VERIFICATION OF GROUND-TRUTH SAMPLES WITH CORRECTED YBUS:")
    print("Active Power (P) Mismatch:")
    print(f"  Mean:   {np.mean(mis_P_all):.6f} pu ({np.mean(mis_P_all)*100:.4f} MW)")
    print(f"  Max:    {np.max(mis_P_all):.6f} pu ({np.max(mis_P_all)*100:.4f} MW)")
    print("Reactive Power (Q) Mismatch:")
    print(f"  Mean:   {np.mean(mis_Q_all):.6f} pu ({np.mean(mis_Q_all)*100:.4f} Mvar)")
    print(f"  Max:    {np.max(mis_Q_all):.6f} pu ({np.max(mis_Q_all)*100:.4f} Mvar)")
    print("=========================================")

if __name__ == "__main__":
    dataset_path = "/app/data_collector/data/ieee39_telemetry_dataset.csv"
    verify_gt_physics(dataset_path)
