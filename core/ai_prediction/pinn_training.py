import os
import csv
import time
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from core.ai_prediction.dataset_loader import TelemetryDataset
from core.ai_prediction.pinn_model import PhysicsInformedPredictorLSTM
from core.ai_prediction.physics_informed_loss import compute_pinn_loss

# Configure paths
AI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.abspath(os.path.join(AI_DIR, "data", "telemetry_dataset_synthetic.csv"))
MODEL_DIR = os.path.join(AI_DIR, "models")
CHECKPOINT_PATH = os.path.join(MODEL_DIR, "lstm_pinn_cyber_physical_predictor.pt")
CHECKPOINT_PATH_ALT = os.path.join(MODEL_DIR, "pinn_cyber_physical_predictor.pt")

os.makedirs(MODEL_DIR, exist_ok=True)

def generate_synthetic_dataset(num_samples=250):
    """
    Generates realistic synthetic IEEE 9-bus grid telemetry data with 83 columns
    for bootstrap fallback if telemetry_dataset.csv is empty/missing/corrupted.
    """
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    
    headers = [
        "timestamp",
        # Bus voltages (9)
        "bus_1_v", "bus_2_v", "bus_3_v", "bus_4_v", "bus_5_v", "bus_6_v", "bus_7_v", "bus_8_v", "bus_9_v",
        # Bus voltage angles (9)
        "bus_1_angle", "bus_2_angle", "bus_3_angle", "bus_4_angle", "bus_5_angle", "bus_6_angle", "bus_7_angle", "bus_8_angle", "bus_9_angle",
        # Bus active power injections (9)
        "bus_1_P", "bus_2_P", "bus_3_P", "bus_4_P", "bus_5_P", "bus_6_P", "bus_7_P", "bus_8_P", "bus_9_P",
        # Bus reactive power injections (9)
        "bus_1_Q", "bus_2_Q", "bus_3_Q", "bus_4_Q", "bus_5_Q", "bus_6_Q", "bus_7_Q", "bus_8_Q", "bus_9_Q",
        # Line active power flows (9)
        "line_L1_4_P", "line_L2_7_P", "line_L3_9_P", "line_L4_5_P", "line_L4_9_P", "line_L5_6_P", "line_L6_7_P", "line_L7_8_P", "line_L8_9_P",
        # Line reactive power flows (9)
        "line_L1_4_Q", "line_L2_7_Q", "line_L3_9_Q", "line_L4_5_Q", "line_L4_9_Q", "line_L5_6_Q", "line_L6_7_Q", "line_L7_8_Q", "line_L8_9_Q",
        # Line currents in p.u. (9)
        "line_L1_4_I", "line_L2_7_I", "line_L3_9_I", "line_L4_5_I", "line_L4_9_I", "line_L5_6_I", "line_L6_7_I", "line_L7_8_I", "line_L8_9_I",
        # Breaker states (9)
        "breaker_L1_4", "breaker_L2_7", "breaker_L3_9", "breaker_L4_5", "breaker_L4_9", "breaker_L5_6", "breaker_L6_7", "breaker_L7_8", "breaker_L8_9",
        # Cyber indicators & decision states (10)
        "anomaly_score",
        "threat_score",
        "attack_active",
        "flisr_state_encoded",
        "attack_type",
        "fdia_active",
        "replay_active",
        "breaker_attack_active",
        "cascade_probability",
        "propagation_risk_encoded"
    ]
    
    start_time = int(time.time() * 1000)
    rows = []
    
    for i in range(num_samples):
        timestamp = start_time + i * 1000
        
        # Nominal system parameters
        voltages = [round(1.0 + random.uniform(-0.015, 0.015), 4) for _ in range(9)]
        angles = [round(random.uniform(-0.08, 0.08), 4) for _ in range(9)]
        
        # Bus active injections
        bus_Ps = [0.0] * 9
        bus_Ps[0] = 72.0  # slack active
        bus_Ps[1] = 163.0 # gen 2
        bus_Ps[2] = 85.0  # gen 3
        bus_Ps[4] = -125.0 # load 5
        bus_Ps[5] = -90.0  # load 6
        bus_Ps[7] = -100.0 # load 8
        bus_Ps = [round(val + random.uniform(-2.0, 2.0), 2) for val in bus_Ps]
        
        # Bus reactive injections
        bus_Qs = [0.0] * 9
        bus_Qs[0] = 27.0
        bus_Qs[1] = 6.0
        bus_Qs[2] = -10.0
        bus_Qs[4] = -50.0
        bus_Qs[5] = -30.0
        bus_Qs[7] = -35.0
        bus_Qs = [round(val + random.uniform(-1.0, 1.0), 2) for val in bus_Qs]
        
        # Line active and reactive flows
        line_Ps = [round(random.uniform(-150.0, 150.0), 2) for _ in range(9)]
        line_Qs = [round(random.uniform(-50.0, 50.0), 2) for _ in range(9)]
        line_Is = [round(random.uniform(0.1, 1.5), 4) for _ in range(9)]
        
        breakers = [1] * 9
        breakers[7] = 0  # L7_8 normally open tie-line
        
        anomaly = round(random.uniform(0.0001, 0.0005), 6)
        threat = 0
        attack_active = 0
        flisr_state = 0  # NORMAL
        attack_type = 0
        fdia_active = 0
        replay_active = 0
        breaker_attack_active = 0
        cascade_prob = 0.0
        prop_risk = 0
        
        # Cyber attack simulation phase
        if 80 <= i < 160:
            attack_active = 1
            voltages[4] = round(voltages[4] - (i - 80) * 0.008, 4)
            voltages[8] = round(voltages[8] - (i - 80) * 0.004, 4)
            anomaly = round(0.004 + (i - 80) * 0.0005, 6)
            threat = int(min(100, (i - 80) * 2.0))
            cascade_prob = round(min(1.0, (i - 80) * 0.02), 2)
            prop_risk = 1 if i < 110 else 2
            
            if 80 <= i < 105:
                fdia_active = 1
                attack_type = 1
            elif 105 <= i < 130:
                replay_active = 1
                attack_type = 2
            elif 130 <= i < 160:
                breaker_attack_active = 1
                attack_type = 3
                breakers[3] = 0  # L4_5 open
                flisr_state = 1  # FAULT_DETECTED
                
        # FLISR Restoration Phase
        elif 160 <= i:
            breakers[3] = 0
            breakers[7] = 1  # restoration tie closed
            flisr_state = 4  # RESTORED
            threat = int(max(0, 80 - (i - 160) * 4))
            voltages[4] = round(voltages[4] + (i - 160) * 0.006, 4)
            cascade_prob = round(max(0.0, 0.8 - (i - 160) * 0.05), 2)
            prop_risk = 0
            
        rows.append([
            timestamp,
            *voltages,
            *angles,
            *bus_Ps,
            *bus_Qs,
            *line_Ps,
            *line_Qs,
            *line_Is,
            *breakers,
            anomaly,
            threat,
            attack_active,
            flisr_state,
            attack_type,
            fdia_active,
            replay_active,
            breaker_attack_active,
            cascade_prob,
            prop_risk
        ])
        
    with open(CSV_PATH, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    print(f"Generated synthetic 83-column dataset with {num_samples} samples at: {CSV_PATH}")

def run_training():
    # 1. Check if dataset exists and has sufficient rows/columns
    dataset_exists = os.path.exists(CSV_PATH)
    has_sufficient_rows = False
    
    if dataset_exists:
        try:
            with open(CSV_PATH, "r") as f:
                reader = csv.reader(f)
                header = next(reader)
                row_count = sum(1 for line in reader)
            if len(header) == 83 and row_count >= 100:
                has_sufficient_rows = True
        except Exception:
            pass
            
    if not dataset_exists or not has_sufficient_rows:
        print("Dataset missing or insufficient columns. Activating 83-column synthetic data fallback...")
        generate_synthetic_dataset(250)
        
    # 2. Instantiate dataset loader
    window_size = 10
    dataset = TelemetryDataset(
        CSV_PATH,
        window_size=window_size,
        target_index=list(range(1, 83)),
        return_cyber_label=False,
        multi_horizon=True
    )
    print(f"Loaded dataset: {len(dataset)} sequence windows constructed.")
    
    # 3. Train-Test Split (80% Train, 20% Validation)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    # 4. Instantiate model (output count = 38)
    first_seq, _ = dataset[0]
    feature_dim = first_seq.shape[1]
    
    print(f"PINN Model dimensions: Sequence Length = {window_size}, Input Feature Count = {feature_dim}, Output Count per Horizon = 38")
    model = PhysicsInformedPredictorLSTM(input_dim=feature_dim, output_dim=38, hidden_dim=128, num_layers=2)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    epochs = 15
    print(f"Starting Multi-Horizon Physics-Informed LSTM training loop ({epochs} epochs)...")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_supervised = 0.0
        train_physics = 0.0
        
        for x_batch, (y10_batch, y30_batch, y60_batch) in train_loader:
            optimizer.zero_grad()
            
            # Physics-Adversarial Robustness training:
            # Perturb inputs (e.g. inject random cyber tampering anomalies on voltage channels)
            # on 30% of the training batches.
            if random.random() < 0.3:
                noise = torch.randn_like(x_batch) * 0.01
                # Perturb voltage fields (indices 0 to 8) to simulate cyberattacks
                noise[:, :, 0:9] += torch.randn(x_batch.shape[0], x_batch.shape[1], 9) * 0.04
                x_batch = torch.clamp(x_batch + noise, 0.0, 1.0)
            
            # Predict horizons
            pred_10, pred_30, pred_60 = model(x_batch)
            
            # Compute loss for each horizon and aggregate
            loss_10, details_10 = compute_pinn_loss(pred_10, y10_batch)
            loss_30, details_30 = compute_pinn_loss(pred_30, y30_batch)
            loss_60, details_60 = compute_pinn_loss(pred_60, y60_batch)
            
            # Joint PINN loss
            loss = loss_10 + loss_30 + loss_60
            
            loss.backward()
            
            # Gradient clipping to prevent gradient explosion and stabilize long-horizon predictions
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            
            train_loss += loss.item() * x_batch.size(0)
            train_supervised += (details_10["loss_supervised"] + details_30["loss_supervised"] + details_60["loss_supervised"]) * x_batch.size(0)
            train_physics += (
                details_10["loss_kcl"] + details_10["loss_kvl"] + details_10["loss_dc_flow"] + details_10["loss_topo"] + details_10["loss_stability"] +
                details_30["loss_kcl"] + details_30["loss_kvl"] + details_30["loss_dc_flow"] + details_30["loss_topo"] + details_30["loss_stability"] +
                details_60["loss_kcl"] + details_60["loss_kvl"] + details_60["loss_dc_flow"] + details_60["loss_topo"] + details_60["loss_stability"]
            ) * x_batch.size(0)
                              
        train_loss /= len(train_dataset)
        train_supervised /= len(train_dataset)
        train_physics /= len(train_dataset)
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, (y10_batch, y30_batch, y60_batch) in val_loader:
                pred_10, pred_30, pred_60 = model(x_batch)
                loss_10, _ = compute_pinn_loss(pred_10, y10_batch)
                loss_30, _ = compute_pinn_loss(pred_30, y30_batch)
                loss_60, _ = compute_pinn_loss(pred_60, y60_batch)
                loss = loss_10 + loss_30 + loss_60
                val_loss += loss.item() * x_batch.size(0)
        val_loss /= len(val_dataset)
        
        print(f"Epoch [{epoch}/{epochs}] - Loss: {train_loss:.6f} (Sup: {train_supervised:.4f}, Phys: {train_physics:.4f}) | Val Loss: {val_loss:.6f}")
        
    # Save checkpoints to both requested paths
    checkpoint_state = {
        "state_dict": model.state_dict(),
        "min_vals": dataset.min_vals.tolist(),
        "max_vals": dataset.max_vals.tolist()
    }
    torch.save(checkpoint_state, CHECKPOINT_PATH)
    torch.save(checkpoint_state, CHECKPOINT_PATH_ALT)
    print(f"Model checkpoints saved successfully to:")
    print(f"  - {CHECKPOINT_PATH}")
    print(f"  - {CHECKPOINT_PATH_ALT}")
    
    # 8. Post-train sample inference validation
    model.eval()
    test_seq, (y10, y30, y60) = val_dataset[0]
    test_input = test_seq.unsqueeze(0)
    
    with torch.no_grad():
        out_10, out_30, out_60 = model(test_input)
        pred_10 = out_10.squeeze(0).numpy()
        pred_30 = out_30.squeeze(0).numpy()
        pred_60 = out_60.squeeze(0).numpy()
        
    print(f"\n--- PINN Validation Inference Test ---")
    print(f"Pred 10s: {pred_10[:3]} ... Shape: {pred_10.shape}")
    print(f"Pred 30s: {pred_30[:3]} ... Shape: {pred_30.shape}")
    print(f"Pred 60s: {pred_60[:3]} ... Shape: {pred_60.shape}")
    
    # Verify no NaNs
    assert not np.isnan(pred_10).any(), "NaN found in 10s prediction!"
    assert not np.isnan(pred_30).any(), "NaN found in 30s prediction!"
    assert not np.isnan(pred_60).any(), "NaN found in 60s prediction!"
    print("Inference verification successful. No NaNs detected.")

if __name__ == "__main__":
    run_training()
