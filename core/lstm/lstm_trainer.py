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

from lstm_model import IEEE39LSTMClassifier
from lstm_evaluator import evaluate_lstm_performance, LABEL_MAP
from core.ai_training.temporal_split import chronological_label_partitions, window_spans

def create_sequences(features, labels, seq_len):
    """
    Creates overlapping sequences of length seq_len.
    The label for each sequence is the label of the last step.
    """
    X = []
    y = []
    for i in range(len(features) - seq_len + 1):
        X.append(features[i : i + seq_len])
        y.append(labels[i + seq_len - 1])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)

def _partition_sequences(df_valid, feature_cols, seq_len):
    features = df_valid[feature_cols].values.astype(np.float32)
    labels = df_valid["label"].map(LABEL_MAP).values.astype(np.int64)
    partitions = chronological_label_partitions(df_valid)
    result = {}
    for name, partition in partitions.items():
        spans = window_spans(partition.raw_indices, seq_len)
        result[name] = (
            np.asarray([features[span] for span in spans], dtype=np.float32),
            np.asarray([labels[span[-1]] for span in spans], dtype=np.int64),
        )
    return result


def train_model_for_window(df_valid, feature_cols, seq_len, epochs=15, batch_size=128, lr=0.002, device="cpu"):
    """
    Trains an LSTM model for a specific window size.
    Returns the trained model, history of metrics, and validation accuracy.
    """
    print(f"\n--- Training for Window Size: {seq_len} ---")
    
    split = _partition_sequences(df_valid, feature_cols, seq_len)
    X_train, y_train = split["train"]
    X_val, y_val = split["validation"]
    X_test, y_test = split["test"]
    n_samples = sum(len(values[0]) for values in split.values())
    
    # Fit scaler parameters from training sequences
    train_mean = X_train.mean(axis=(0, 1))
    train_std = X_train.std(axis=(0, 1))
    train_std[train_std < 1e-8] = 1.0  # Prevent division by zero
    
    # Initialize Model
    model = IEEE39LSTMClassifier(
        input_dim=156,
        hidden_dim=64,
        num_layers=2,
        num_classes=8,
        dropout=0.2
    ).to(device)
    
    # Copy normalization parameters to model buffers
    model.mean.copy_(torch.tensor(train_mean, dtype=torch.float32).to(device))
    model.std.copy_(torch.tensor(train_std, dtype=torch.float32).to(device))
    
    # Setup DataLoaders
    train_dataset = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    val_dataset = TensorDataset(torch.tensor(X_val), torch.tensor(y_val))
    test_dataset = TensorDataset(torch.tensor(X_test), torch.tensor(y_test))
    
    generator = torch.Generator().manual_seed(42)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, generator=generator)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    # Optimizer and Loss
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    criterion = nn.CrossEntropyLoss()
    
    history = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": []
    }
    
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        correct = 0
        total = 0
        
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item() * batch_x.size(0)
            preds = torch.argmax(logits, dim=-1)
            correct += (preds == batch_y).sum().item()
            total += batch_x.size(0)
            
        epoch_loss /= len(X_train)
        epoch_acc = correct / total
        
        # Validation Pass
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)
                
                logits = model(batch_x)
                loss = criterion(logits, batch_y)
                val_loss += loss.item() * batch_x.size(0)
                
                preds = torch.argmax(logits, dim=-1)
                val_correct += (preds == batch_y).sum().item()
                val_total += batch_x.size(0)
                
        val_loss /= len(X_val)
        val_acc = val_correct / val_total
        
        history["train_loss"].append(epoch_loss)
        history["train_acc"].append(epoch_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {epoch_loss:.4f} Acc: {epoch_acc*100:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%")
            
    return model, history, val_acc, test_loader, n_samples

def run_lstm_pipeline(dataset_path: str, device: str = "cpu", output_dir: str = None):
    torch.manual_seed(42)
    np.random.seed(42)
    print("=========================================")
    print("STARTING TEMPORAL LSTM TRAINING PIPELINE")
    print("=========================================")
    
    # 1. Load and clean dataset
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")
        
    df = pd.read_csv(dataset_path)
    exclude_labels = ["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"]
    df_valid = df[~df["label"].isin(exclude_labels)].copy().reset_index(drop=True)
    print(f"Loaded valid samples: {len(df_valid)}")
    
    # Extract feature columns list
    p_cols = [f"bus_{i}_P" for i in range(1, 40)]
    q_cols = [f"bus_{i}_Q" for i in range(1, 40)]
    v_cols = [f"bus_{i}_V" for i in range(1, 40)]
    theta_cols = [f"bus_{i}_theta" for i in range(1, 40)]
    feature_cols = p_cols + q_cols + v_cols + theta_cols
    
    # 2. Evaluate window sizes: 5, 10, 20
    window_sizes = [5, 10, 20]
    best_window = None
    best_val_acc = -1.0
    best_model = None
    best_history = None
    best_test_loader = None
    best_total_sequences = 0
    
    for ws in window_sizes:
        model, history, val_acc, test_loader, total_sequences = train_model_for_window(
            df_valid, feature_cols, ws, epochs=15, batch_size=128, lr=0.002, device=device
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_window = ws
            best_model = model
            best_history = history
            best_test_loader = test_loader
            best_total_sequences = total_sequences
            
    print("\n=========================================")
    print(f"SELECTED BEST TEMPORAL WINDOW: {best_window}-step")
    print(f"Validation Accuracy: {best_val_acc*100:.2f}%")
    print("=========================================")
    
    # 3. Model Serialization
    output_dir = output_dir or current_dir
    os.makedirs(output_dir, exist_ok=True)
    model_save_path = os.path.join(output_dir, "trained_lstm_model.pt")
    torch.save(best_model.state_dict(), model_save_path)
    print(f"Model saved to: {model_save_path}")
    
    # 4. Save best training history metrics
    metrics_save_path = os.path.join(output_dir, "training_metrics.json")
    with open(metrics_save_path, "w") as f:
        json.dump(best_history, f, indent=4)
    print(f"Training metrics saved to: {metrics_save_path}")
    
    # 5. Evaluate on Test set
    print("\nRunning final test set evaluation...")
    eval_results = evaluate_lstm_performance(best_model, best_test_loader, device=device)
    
    # Save evaluation results to file
    eval_save_path = os.path.join(output_dir, "evaluation_results.json")
    with open(eval_save_path, "w") as f:
        json.dump(eval_results, f, indent=4)
    print(f"Evaluation results saved to: {eval_save_path}")
    
    # Print results summary
    print("\n=========================================")
    print("TEST EVALUATION PERFORMANCE")
    print("=========================================")
    print(f"Test Accuracy           : {eval_results['accuracy']*100:.2f}%")
    print(f"Test F1 Score (Weighted): {eval_results['f1_weighted']:.4f}")
    print(f"Test F1 Score (Macro)   : {eval_results['f1_macro']:.4f}")
    print("Confusion Matrix:")
    for row in eval_results["confusion_matrix"]:
        print("  ", row)
    print("=========================================")
    
    return best_window, best_val_acc, eval_results, best_total_sequences

if __name__ == "__main__":
    dataset_path = os.path.join(parent_dir, "data_collector", "data", "ieee39_telemetry_dataset.csv")
    run_lstm_pipeline(dataset_path)
