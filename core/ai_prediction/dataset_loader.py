import os
import csv
import numpy as np
import torch
from torch.utils.data import Dataset

class TelemetryDataset(Dataset):
    def __init__(self, csv_path, window_size=10, target_index=5, min_vals=None, max_vals=None, return_cyber_label=False, multi_horizon=False):
        self.window_size = window_size
        self.target_index = target_index
        self.return_cyber_label = return_cyber_label
        self.multi_horizon = multi_horizon
        
        if isinstance(target_index, list):
            self.target_indices = target_index
        else:
            self.target_indices = [target_index]
            
        # Load CSV using built-in csv reader
        raw_rows = []
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Telemetry dataset CSV not found at: {csv_path}")
            
        with open(csv_path, mode="r", newline="") as f:
            reader = csv.reader(f)
            header = [h.strip() for h in next(reader)] # skip headers
            for row in reader:
                if row: # skip empty lines
                    raw_rows.append(row)
                    
        # Check for missing headers and map dynamically to preserve backward compatibility
        header_to_idx = {name: i for i, name in enumerate(header)}
        
        # New 83-column expected headers (excluding timestamp is 82 features)
        new_headers = [
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

        # Legacy headers for backward compatibility mapping
        legacy_headers = [
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

        # Decide which schema we are targeting for data output
        expected_headers = new_headers if self.multi_horizon else legacy_headers
        
        # Map target indices to expected_headers indices if passed as strings
        target_indices_mapped = []
        for t in self.target_indices:
            if isinstance(t, str):
                if t in expected_headers:
                    target_indices_mapped.append(expected_headers.index(t))
                else:
                    raise ValueError(f"Target column {t} not found in expected headers.")
            else:
                target_indices_mapped.append(int(t))
        self.target_indices = target_indices_mapped
        
        data_matrix = []
        for row in raw_rows:
            new_row = []
            for col_name in expected_headers:
                if col_name in header_to_idx:
                    try:
                        new_row.append(float(row[header_to_idx[col_name]]))
                    except ValueError:
                        new_row.append(0.0)
                # Backward compatibility fallback: map line_L_load from line_L_I
                elif col_name.endswith("_load") and col_name.replace("_load", "_I") in header_to_idx:
                    try:
                        current_val = float(row[header_to_idx[col_name.replace("_load", "_I")]])
                        new_row.append(current_val * (100.0 / 3.0))
                    except ValueError:
                        new_row.append(0.0)
                # Backward compatibility fallback: map line_L_I from line_L_load
                elif col_name.endswith("_I") and col_name.replace("_I", "_load") in header_to_idx:
                    try:
                        load_val = float(row[header_to_idx[col_name.replace("_I", "_load")]])
                        new_row.append(load_val * (3.0 / 100.0))
                    except ValueError:
                        new_row.append(0.0)
                else:
                    new_row.append(0.0)
            data_matrix.append(new_row)
            
        data = np.array(data_matrix, dtype=np.float32)
        if len(data) <= window_size + (60 if self.multi_horizon else 0):
            raise ValueError(f"Dataset has only {len(data)} samples, which is insufficient for window_size={window_size}")
            
        # Feature indices exclude timestamp (index 0) and target_indices (unless multi_horizon is True)
        if self.multi_horizon:
            self.feature_indices = list(range(1, len(expected_headers)))
        else:
            self.feature_indices = [i for i in range(1, len(expected_headers)) if i not in self.target_indices]
        
        X_raw = data[:, self.feature_indices]
        y_raw = data[:, self.target_indices]
        
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
        
        if self.multi_horizon:
            self.X_seq = []
            self.y_10_seq = []
            self.y_30_seq = []
            self.y_60_seq = []
            
            # Extract matrices for target computation
            voltages = data[:, 1:10]
            line_Ps = data[:, 37:46]
            line_Qs = data[:, 46:55]
            
            # Compute cyber instability at each step
            voltages_out = np.any((voltages < 0.95) | (voltages > 1.05), axis=1)
            attack_indicators = (
                (data[:, 75] == 1.0) |  # attack_active
                (data[:, 78] == 1.0) |  # fdia_active
                (data[:, 79] == 1.0) |  # replay_active
                (data[:, 80] == 1.0) |  # breaker_attack_active
                (data[:, 74] > 40.0)    # threat_score
            )
            cyber_instability = (voltages_out & attack_indicators).astype(np.float32)
            
            # Construct target matrix (len(data), 83)
            # targets contains all 82 features + 1 cyber label = 83 columns
            targets = np.hstack([
                data[:, 1:],
                cyber_instability.reshape(-1, 1)
            ])
            
            for i in range(len(data) - window_size - 60):
                self.X_seq.append(X_scaled[i : i + window_size])
                # t is the index of the last element in the window: i + window_size - 1
                # Horizons are t + 10, t + 30, t + 60
                self.y_10_seq.append(targets[i + window_size + 9])
                self.y_30_seq.append(targets[i + window_size + 29])
                self.y_60_seq.append(targets[i + window_size + 59])
                
            self.X_seq = np.array(self.X_seq, dtype=np.float32)
            self.y_10_seq = np.array(self.y_10_seq, dtype=np.float32)
            self.y_30_seq = np.array(self.y_30_seq, dtype=np.float32)
            self.y_60_seq = np.array(self.y_60_seq, dtype=np.float32)
        else:
            # Normalize targets:
            # If target is threat score (index 29), map [0, 100] -> [0.0, 1.0]
            # Voltages are kept raw as they reside in [0.0, 1.2] p.u.
            y_scaled = np.zeros_like(y_raw)
            for idx, t_idx in enumerate(self.target_indices):
                if t_idx == 29:
                    y_scaled[:, idx] = y_raw[:, idx] / 100.0
                else:
                    y_scaled[:, idx] = y_raw[:, idx]
                    
            # Generate ground-truth cyber instability labels (legacy indexing)
            voltages_out = np.any((y_raw < 0.95) | (y_raw > 1.05), axis=1)
            attack_indicators = (
                (data[:, 30] == 1.0) |  # attack_active
                (data[:, 33] == 1.0) |  # fdia_active
                (data[:, 34] == 1.0) |  # replay_active
                (data[:, 35] == 1.0) |  # breaker_attack_active
                (data[:, 29] > 40.0)    # threat_score
            )
            cyber_instability = (voltages_out & attack_indicators).astype(np.float32)
            
            # Construct sequential sliding windows
            self.X_seq = []
            self.y_seq = []
            self.cyber_seq = []
            
            for i in range(len(data) - window_size):
                self.X_seq.append(X_scaled[i : i + window_size])
                self.y_seq.append(y_scaled[i + window_size])
                self.cyber_seq.append(cyber_instability[i + window_size])
                
            self.X_seq = np.array(self.X_seq, dtype=np.float32)
            self.y_seq = np.array(self.y_seq, dtype=np.float32)
            self.cyber_seq = np.array(self.cyber_seq, dtype=np.float32)
            
            if len(self.target_indices) == 1:
                self.y_seq = self.y_seq.reshape(-1, 1)

    def __len__(self):
        return len(self.X_seq)

    def __getitem__(self, idx):
        if self.multi_horizon:
            X_tensor = torch.tensor(self.X_seq[idx])
            y_10_tensor = torch.tensor(self.y_10_seq[idx])
            y_30_tensor = torch.tensor(self.y_30_seq[idx])
            y_60_tensor = torch.tensor(self.y_60_seq[idx])
            return X_tensor, (y_10_tensor, y_30_tensor, y_60_tensor)
        else:
            if self.return_cyber_label:
                y_voltages = torch.tensor(self.y_seq[idx])
                y_cyber = torch.tensor([self.cyber_seq[idx]], dtype=torch.float32)
                return torch.tensor(self.X_seq[idx]), (y_voltages, y_cyber)
            else:
                return torch.tensor(self.X_seq[idx]), torch.tensor(self.y_seq[idx])
