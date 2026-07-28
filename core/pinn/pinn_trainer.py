import os
import sys
import json
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import DataLoader

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))


from pinn_model import IEEE39PINNAutoencoder
from physics_loss import IEEE39PhysicsLoss
from pinn_evaluator import evaluate_pinn

def train_val_test_split(data, train_frac=0.70, val_frac=0.15, random_seed=42):
    np.random.seed(random_seed)
    n = len(data)
    indices = np.random.permutation(n)
    
    train_end = int(train_frac * n)
    val_end = train_end + int(val_frac * n)
    
    train_idx = indices[:train_end]
    val_idx = indices[train_end:val_end]
    test_idx = indices[val_end:]
    
    return data[train_idx], data[val_idx], data[test_idx]

def train_pinn(
    dataset_path: str,
    epochs: int = 50,
    batch_size: int = 128,
    lr: float = 0.001,
    physics_weight: float = 0.5,
    device: str = "cpu"
):
    print("=========================================")
    print("STARTING PINN TRAINING PIPELINE")
    print("=========================================")
    
    # 1. Load dataset
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")
        
    print(f"Loading dataset from: {dataset_path}")
    df = pd.read_csv(dataset_path)
    print(f"Total samples in raw dataset: {len(df)}")
    
    # 2. Filter valid samples (Exclude NON_CONVERGED, BLACKOUT, INVALID_STATE)
    exclude_labels = ["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"]
    df_valid = df[~df["label"].isin(exclude_labels)].copy()
    print(f"Filtered to physics-valid samples: {len(df_valid)}")
    
    # 3. Extract features: P (39), Q (39), V (39), theta (39)
    p_cols = [f"bus_{i}_P" for i in range(1, 40)]
    q_cols = [f"bus_{i}_Q" for i in range(1, 40)]
    v_cols = [f"bus_{i}_V" for i in range(1, 40)]
    theta_cols = [f"bus_{i}_theta" for i in range(1, 40)]
    feature_cols = p_cols + q_cols + v_cols + theta_cols
    
    # Verify we got 156 features
    assert len(feature_cols) == 156, f"Expected 156 features, got {len(feature_cols)}"
    
    # Extract data
    data_all = df_valid[feature_cols].values.astype(np.float32)
    
    # 4. Split dataset (70% Train, 15% Val, 15% Test)
    train_data, val_data, test_data = train_val_test_split(data_all, train_frac=0.70, val_frac=0.15, random_seed=42)

    
    print(f"Dataset Split: Train={len(train_data)}, Val={len(val_data)}, Test={len(test_data)}")
    
    # 5. Initialize Model
    model = IEEE39PINNAutoencoder(input_dim=156, hidden_dim=64).to(device)
    
    # Compute and set training mean/std for internal normalization
    train_mean = train_data.mean(axis=0)
    train_std = train_data.std(axis=0)
    # Prevent division by zero
    train_std[train_std < 1e-8] = 1.0
    
    model.mean.copy_(torch.tensor(train_mean, dtype=torch.float32).to(device))
    model.std.copy_(torch.tensor(train_std, dtype=torch.float32).to(device))
    
    # 6. Initialize loss functions and optimizer
    physics_loss_fn = IEEE39PhysicsLoss(device=device)
    mse_loss_fn = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    
    # Create DataLoaders
    # Note: iterating over a Tensor yields rows directly, matching evaluator requirements
    train_tensor = torch.tensor(train_data, dtype=torch.float32)
    val_tensor = torch.tensor(val_data, dtype=torch.float32)
    test_tensor = torch.tensor(test_data, dtype=torch.float32)
    
    train_loader = DataLoader(train_tensor, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_tensor, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_tensor, batch_size=batch_size, shuffle=False)
    
    # 7. Training Loop
    metrics_history = {
        "train_loss": [],
        "train_data_loss": [],
        "train_physics_loss": [],
        "val_loss": [],
        "val_data_loss": [],
        "val_physics_loss": []
    }
    
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_train_loss = 0.0
        epoch_train_data_loss = 0.0
        epoch_train_physics_loss = 0.0
        
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            
            # Forward pass
            reconstructed, pred_P, pred_Q, pred_V, pred_theta = model(batch)
            
            # Compute data reconstruction loss in normalized space to prevent scale dominance
            batch_norm = (batch - model.mean) / (model.std + 1e-8)
            reconstructed_norm = (reconstructed - model.mean) / (model.std + 1e-8)
            loss_data = mse_loss_fn(reconstructed_norm, batch_norm)
            
            # Compute physics loss
            loss_physics, _ = physics_loss_fn(pred_P, pred_Q, pred_V, pred_theta)
            
            # Combined Loss
            loss_total = loss_data + physics_weight * loss_physics
            
            loss_total.backward()
            optimizer.step()
            
            epoch_train_loss += loss_total.item() * batch.size(0)
            epoch_train_data_loss += loss_data.item() * batch.size(0)
            epoch_train_physics_loss += loss_physics.item() * batch.size(0)
            
        epoch_train_loss /= len(train_data)
        epoch_train_data_loss /= len(train_data)
        epoch_train_physics_loss /= len(train_data)
        
        # Validation pass
        model.eval()
        epoch_val_loss = 0.0
        epoch_val_data_loss = 0.0
        epoch_val_physics_loss = 0.0
        
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                reconstructed, pred_P, pred_Q, pred_V, pred_theta = model(batch)
                
                batch_norm = (batch - model.mean) / (model.std + 1e-8)
                reconstructed_norm = (reconstructed - model.mean) / (model.std + 1e-8)
                loss_data = mse_loss_fn(reconstructed_norm, batch_norm)
                
                loss_physics, _ = physics_loss_fn(pred_P, pred_Q, pred_V, pred_theta)
                
                loss_total = loss_data + physics_weight * loss_physics
                
                epoch_val_loss += loss_total.item() * batch.size(0)
                epoch_val_data_loss += loss_data.item() * batch.size(0)
                epoch_val_physics_loss += loss_physics.item() * batch.size(0)
                
        epoch_val_loss /= len(val_data)
        epoch_val_data_loss /= len(val_data)
        epoch_val_physics_loss /= len(val_data)
        
        # Record metrics
        metrics_history["train_loss"].append(epoch_train_loss)
        metrics_history["train_data_loss"].append(epoch_train_data_loss)
        metrics_history["train_physics_loss"].append(epoch_train_physics_loss)
        metrics_history["val_loss"].append(epoch_val_loss)
        metrics_history["val_data_loss"].append(epoch_val_data_loss)
        metrics_history["val_physics_loss"].append(epoch_val_physics_loss)
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:02d}/{epochs:02d} | "
                  f"Train Loss: {epoch_train_loss:.5f} (Data: {epoch_train_data_loss:.5f}, Phys: {epoch_train_physics_loss:.5f}) | "
                  f"Val Loss: {epoch_val_loss:.5f} (Data: {epoch_val_data_loss:.5f}, Phys: {epoch_val_physics_loss:.5f})")
            
    print("\nTraining complete.")
    
    # 8. Model Serialization
    model_save_path = os.path.join(current_dir, "trained_pinn_model.pt")
    torch.save(model.state_dict(), model_save_path)
    print(f"Model saved to: {model_save_path}")
    
    # Save training metrics history
    metrics_save_path = os.path.join(current_dir, "training_metrics.json")
    with open(metrics_save_path, "w") as f:
        json.dump(metrics_history, f, indent=4)
    print(f"Training metrics saved to: {metrics_save_path}")
    
    # 9. Model Evaluation on Test set
    print("\nRunning final evaluation on Test Set...")
    eval_metrics, eval_results = evaluate_pinn(model, test_loader, physics_loss_fn, device=device)
    
    # Save evaluation results
    eval_save_path = os.path.join(current_dir, "evaluation_results.json")
    with open(eval_save_path, "w") as f:
        json.dump(eval_results, f, indent=4)
    print(f"Evaluation results saved to: {eval_save_path}")
    
    print("\nTraining pipeline successfully completed.")

if __name__ == "__main__":
    dataset_path = os.path.join(parent_dir, "data_collector", "data", "ieee39_telemetry_dataset.csv")
    train_pinn(dataset_path=dataset_path, epochs=60, batch_size=128, lr=0.001, physics_weight=0.005)



