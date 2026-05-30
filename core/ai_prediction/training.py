import os
import csv
import time
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from core.ai_prediction.dataset_loader import TelemetryDataset
from model import TelemetryPredictorLSTM

# Configure paths
AI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.abspath(os.path.join(AI_DIR, "..", "data_collector", "data", "telemetry_dataset.csv"))
MODEL_DIR = os.path.join(AI_DIR, "models")
CHECKPOINT_PATH = os.path.join(MODEL_DIR, "lstm_bus5_predictor.pt")

os.makedirs(MODEL_DIR, exist_ok=True)

def generate_synthetic_dataset(num_samples=100):
    """
    Generates realistic synthetic IEEE 9-bus grid telemetry data
    representing normal states, cyber attack voltage drops on Bus_5,
    and self-healing restoration steps.
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
        "flisr_state_encoded"
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
        
        # Cyber attack simulation phase: samples 50 to 80 (voltage collapse on Bus 5)
        if 50 <= i < 80:
            attack_active = 1
            voltages[4] = round(voltages[4] - (i - 50) * 0.012, 4)  # drop Bus_5 voltage
            loads[3] = round(loads[3] + (i - 50) * 3.5, 2)
            anomaly = round(0.005 + (i - 50) * 0.0008, 6)
            threat = int(min(100, (i - 50) * 3.3))
            
            if i >= 70:
                breakers[3] = 0
                flisr_state = 1
                
        # Self-healing and FLISR restoration phase: samples 80 to 100
        elif 80 <= i:
            breakers[3] = 0
            breakers[7] = 1
            flisr_state = 4
            threat = int(max(0, 80 - (i - 80) * 8))
            voltages[4] = round(voltages[4] + (i - 80) * 0.015, 4)
            
        rows.append([
            timestamp,
            *voltages,
            *loads,
            *breakers,
            anomaly,
            threat,
            attack_active,
            flisr_state
        ])
        
    with open(CSV_PATH, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    print(f"Generated synthetic telemetry dataset with {num_samples} samples at: {CSV_PATH}")

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

    # 2. Instantiate loader targeting Bus_5 voltage (target_index=5)
    window_size = 10
    dataset = TelemetryDataset(CSV_PATH, window_size=window_size, target_index=5)
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
    
    print(f"LSTM dimensions: Sequence Length = {window_size}, Input Feature Count = {feature_dim}")
    model = TelemetryPredictorLSTM(input_dim=feature_dim, hidden_dim=64, num_layers=2, dropout=0.2)
    
    # 5. Define loss function and optimizer
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)

    # 6. Training loop
    epochs = 10
    print(f"Starting LSTM Bus_5 voltage predictor training loop ({epochs} epochs)...")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for x_batch, y_batch in train_loader:
            optimizer.zero_grad()
            predictions = model(x_batch)
            loss = criterion(predictions, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x_batch.size(0)
            
        train_loss /= len(train_dataset)
        
        # Validation evaluation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, y_batch in val_loader:
                predictions = model(x_batch)
                loss = criterion(predictions, y_batch)
                val_loss += loss.item() * x_batch.size(0)
                
        val_loss /= len(val_dataset)
        
        print(f"Epoch [{epoch}/{epochs}] - Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")

    # 7. Save model checkpoint
    torch.save(model.state_dict(), CHECKPOINT_PATH)
    print(f"Model checkpoint saved successfully to: {CHECKPOINT_PATH}")

    # 8. Post-train sample inference validation
    model.eval()
    test_seq, test_target = val_dataset[0]
    test_input = test_seq.unsqueeze(0) # add batch dim
    
    with torch.no_grad():
        pred_val = model(test_input).item()
        
    actual_voltage = round(float(test_target.item()), 4)
    predicted_voltage = round(pred_val, 4)
    
    print(f"\n--- Bus_5 Voltage Validation Inference ---")
    print(f"Input Shape: {test_input.shape}")
    print(f"Actual Bus_5 Voltage: {actual_voltage} p.u.")
    print(f"Predicted Bus_5 Voltage: {predicted_voltage} p.u. (deviation: {abs(actual_voltage - predicted_voltage):.4f})")
    
    assert not np.isnan(pred_val), "Prediction returned NaN value!"
    print("Inference test complete. Validation successful!")

if __name__ == "__main__":
    run_training()
