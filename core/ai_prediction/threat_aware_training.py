import os
import csv
import time
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from dataset_loader import TelemetryDataset
from multi_bus_model import ThreatAwarePredictorLSTM

# Configure paths
AI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.abspath(os.path.join(AI_DIR, "..", "data_collector", "data", "telemetry_dataset.csv"))
MODEL_DIR = os.path.join(AI_DIR, "models")
CHECKPOINT_PATH = os.path.join(MODEL_DIR, "lstm_threat_aware_predictor.pt")

os.makedirs(MODEL_DIR, exist_ok=True)

def generate_synthetic_dataset(num_samples=150):
    """
    Generates realistic synthetic IEEE 9-bus grid telemetry data with cyber context
    for bootstrap fallback if telemetry_dataset.csv is empty/missing.
    """
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    
    headers = [
        "timestamp",
        "bus_1_v", "bus_2_v", "bus_3_v", "bus_4_v", "bus_5_v", "bus_6_v", "bus_7_v", "bus_8_v", "bus_9_v",
        "line_L1_4_load", "line_L2_7_load", "line_L3_9_load", "line_L4_5_load", "line_L4_9_load", "line_L5_6_load", "line_L6_7_load", "line_L7_8_load", "line_L8_9_load",
        "breaker_L1_4", "breaker_L2_7", "breaker_L3_9", "breaker_L4_5", "breaker_L4_9", "breaker_L5_6", "breaker_L6_7", "breaker_L7_8", "breaker_L8_9",
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
        
        # Default normal parameters
        voltages = [round(1.0 + random.uniform(-0.015, 0.015), 4) for _ in range(9)]
        loads = [round(40.0 + random.uniform(-2.0, 2.0), 2) for _ in range(9)]
        breakers = [1] * 9  # 1 represents CLOSED
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
        
        # Cyber attack simulation phase: samples 50 to 80 (voltage collapse on Bus 5 and cascade)
        if 50 <= i < 80:
            attack_active = 1
            voltages[4] = round(voltages[4] - (i - 50) * 0.012, 4)  # drop Bus_5 voltage
            voltages[8] = round(voltages[8] - (i - 50) * 0.006, 4)  # drop Bus_9 voltage
            voltages[0] = round(voltages[0] - (i - 50) * 0.002, 4)  # drift Bus_1 voltage
            loads[3] = round(loads[3] + (i - 50) * 3.5, 2)
            anomaly = round(0.005 + (i - 50) * 0.0008, 6)
            threat = int(min(100, (i - 50) * 3.3))
            cascade_prob = round(min(1.0, (i - 50) * 0.03), 2)
            prop_risk = 1 if i < 65 else 2
            
            # Map specific phases to different attack types
            if 50 <= i < 60:
                fdia_active = 1
                attack_type = 1
            elif 60 <= i < 70:
                replay_active = 1
                attack_type = 2
            elif 70 <= i < 80:
                breaker_attack_active = 1
                attack_type = 3
                breakers[3] = 0
                flisr_state = 1
                
        # Self-healing and FLISR restoration phase: samples 80 to 150
        elif 80 <= i:
            breakers[3] = 0
            breakers[7] = 1
            flisr_state = 4
            threat = int(max(0, 80 - (i - 80) * 8))
            voltages[4] = round(voltages[4] + (i - 80) * 0.015, 4)
            voltages[8] = round(voltages[8] + (i - 80) * 0.008, 4)
            cascade_prob = round(max(0.0, 0.9 - (i - 80) * 0.1), 2)
            prop_risk = 0
            
        rows.append([
            timestamp,
            *voltages,
            *loads,
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
        
    print(f"Generated synthetic threat-aware telemetry dataset with {num_samples} samples at: {CSV_PATH}")

def run_training():
    # 1. Check if dataset exists, fallback to synthetic data if needed
    dataset_exists = os.path.exists(CSV_PATH)
    has_sufficient_rows = False
    if dataset_exists:
        with open(CSV_PATH, "r") as f:
            row_count = sum(1 for line in f)
        if row_count >= 20:
            has_sufficient_rows = True
            
    if not dataset_exists or not has_sufficient_rows:
        print("Dataset missing or insufficient. Activating synthetic data fallback...")
        generate_synthetic_dataset(150)

    # 2. Instantiate loader targeting buses 1, 3, 5, 7, 9 (indices 1, 3, 5, 7, 9)
    window_size = 10
    target_indices = [1, 3, 5, 7, 9]
    dataset = TelemetryDataset(
        CSV_PATH, 
        window_size=window_size, 
        target_index=target_indices, 
        return_cyber_label=True
    )
    print(f"Loaded dataset: {len(dataset)} sequence windows constructed.")

    # 3. Train-Test Split (80% Train, 20% Validation)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False)

    # 4. Instantiate model
    first_seq, _ = dataset[0]
    feature_dim = first_seq.shape[1]
    
    print(f"LSTM dimensions: Sequence Length = {window_size}, Input Feature Count = {feature_dim}, Output Count = 5 voltages + 1 cyber label")
    model = ThreatAwarePredictorLSTM(input_dim=feature_dim, output_dim=5, hidden_dim=64, num_layers=2, dropout=0.2)
    
    # 5. Define loss functions and optimizer
    criterion_reg = nn.MSELoss()
    criterion_cls = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)

    # 6. Training loop
    epochs = 10
    print(f"Starting LSTM threat-aware multi-task training loop ({epochs} epochs)...")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_reg_loss = 0.0
        train_cls_loss = 0.0
        
        for x_batch, (y_volt_batch, y_cyber_batch) in train_loader:
            optimizer.zero_grad()
            pred_volt, pred_cyber_logits = model(x_batch)
            
            loss_reg = criterion_reg(pred_volt, y_volt_batch)
            loss_cls = criterion_cls(pred_cyber_logits, y_cyber_batch)
            
            # Combine losses (alpha weight of 2.0 on classification task to highlight threat detection)
            loss = loss_reg + 2.0 * loss_cls
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * x_batch.size(0)
            train_reg_loss += loss_reg.item() * x_batch.size(0)
            train_cls_loss += loss_cls.item() * x_batch.size(0)
            
        train_loss /= len(train_dataset)
        train_reg_loss /= len(train_dataset)
        train_cls_loss /= len(train_dataset)
        
        # Validation evaluation
        model.eval()
        val_loss = 0.0
        val_reg_loss = 0.0
        val_cls_loss = 0.0
        
        with torch.no_grad():
            for x_batch, (y_volt_batch, y_cyber_batch) in val_loader:
                pred_volt, pred_cyber_logits = model(x_batch)
                loss_reg = criterion_reg(pred_volt, y_volt_batch)
                loss_cls = criterion_cls(pred_cyber_logits, y_cyber_batch)
                loss = loss_reg + 2.0 * loss_cls
                
                val_loss += loss.item() * x_batch.size(0)
                val_reg_loss += loss_reg.item() * x_batch.size(0)
                val_cls_loss += loss_cls.item() * x_batch.size(0)
                
        val_loss /= len(val_dataset)
        val_reg_loss /= len(val_dataset)
        val_cls_loss /= len(val_dataset)
        
        print(f"Epoch [{epoch}/{epochs}] - Loss: {train_loss:.6f} (Reg: {train_reg_loss:.4f}, Cls: {train_cls_loss:.4f}) | Val Loss: {val_loss:.6f} (Reg: {val_reg_loss:.4f}, Cls: {val_cls_loss:.4f})")

    # 7. Save model checkpoint
    torch.save(model.state_dict(), CHECKPOINT_PATH)
    print(f"Model checkpoint saved successfully to: {CHECKPOINT_PATH}")

    # 8. Post-train sample inference validation
    model.eval()
    test_seq, (test_volts, test_cyber) = val_dataset[0]
    test_input = test_seq.unsqueeze(0) # add batch dim
    
    with torch.no_grad():
        pred_volts, pred_cyber_prob = model.predict(test_input)
        pred_volts = pred_volts.squeeze(0).numpy()
        pred_cyber_prob = pred_cyber_prob.squeeze(0).numpy()
        
    actual_volts = test_volts.numpy()
    actual_cyber = test_cyber.numpy()[0]
    
    print(f"\n--- Threat-Aware Validation Inference ---")
    print(f"Input Shape: {test_input.shape}")
    buses_labels = ["Bus_1", "Bus_3", "Bus_5", "Bus_7", "Bus_9"]
    for idx, label in enumerate(buses_labels):
        act_v = round(float(actual_volts[idx]), 4)
        pred_v = round(float(pred_volts[idx]), 4)
        print(f" {label} Voltage -> Actual: {act_v} p.u. | Predicted: {pred_v} p.u. (deviation: {abs(act_v - pred_v):.4f})")
        assert not np.isnan(pred_volts[idx]), f"Prediction for {label} returned NaN value!"
        
    print(f"Cyber-Induced Instability Probability -> Actual: {actual_cyber} | Predicted: {pred_cyber_prob[0]:.4f}")
    assert not np.isnan(pred_cyber_prob[0]), "Prediction for cyber probability returned NaN value!"
    print("Inference test complete. Validation successful!")

if __name__ == "__main__":
    run_training()
