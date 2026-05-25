import os
import csv
import numpy as np
import torch
from torch.utils.data import Dataset

class TelemetryDataset(Dataset):
    def __init__(self, csv_path, window_size=10, target_index=5, min_vals=None, max_vals=None):
        self.window_size = window_size
        self.target_index = target_index
        
        # Load CSV using built-in csv reader
        data = []
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Telemetry dataset CSV not found at: {csv_path}")
            
        with open(csv_path, mode="r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader) # skip headers
            for row in reader:
                if row: # skip empty lines
                    data.append([float(val) for val in row])
                    
        data = np.array(data, dtype=np.float32)
        if len(data) <= window_size:
            raise ValueError(f"Dataset has only {len(data)} samples, which is insufficient for window_size={window_size}")
            
        # Feature indices exclude timestamp (index 0) and the selected target_index
        self.feature_indices = [i for i in range(1, len(header)) if i != self.target_index]
        
        X_raw = data[:, self.feature_indices]
        y_raw = data[:, self.target_index]
        
        # Fit or load min/max scaling values for features
        if min_vals is None:
            self.min_vals = X_raw.min(axis=0)
        else:
            self.min_vals = min_vals
            
        if max_vals is None:
            self.max_vals = X_raw.max(axis=0)
        else:
            self.max_vals = max_vals
            
        # Scale features using Min-Max Scaling, guarding against zero variance
        range_vals = self.max_vals - self.min_vals
        range_vals[range_vals == 0.0] = 1.0
        X_scaled = (X_raw - self.min_vals) / range_vals
        
        # Normalize target:
        # If target is threat score (index 29), map [0, 100] -> [0.0, 1.0]
        # If target is voltage (index 5) or similar, keep unscaled since it lies in [0.0, 1.2] p.u.
        if self.target_index == 29:
            y_scaled = y_raw / 100.0
        else:
            y_scaled = y_raw
        
        # Construct sequential sliding windows
        # X: shape (N - window_size, window_size, feature_dim)
        # y: shape (N - window_size, 1) -> predicts target at step i + window_size
        self.X_seq = []
        self.y_seq = []
        
        for i in range(len(data) - window_size):
            self.X_seq.append(X_scaled[i : i + window_size])
            self.y_seq.append(y_scaled[i + window_size])
            
        self.X_seq = np.array(self.X_seq, dtype=np.float32)
        self.y_seq = np.array(self.y_seq, dtype=np.float32).reshape(-1, 1)

    def __len__(self):
        return len(self.X_seq)

    def __getitem__(self, idx):
        # Return PyTorch-ready tensors
        return torch.tensor(self.X_seq[idx]), torch.tensor(self.y_seq[idx])
