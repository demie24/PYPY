import os
import csv
import math
import sys
import numpy as np
from physics_validator import validate_physics

# Get dataset path
current_dir = os.path.dirname(os.path.abspath(__file__))
dataset_path = os.path.abspath(os.path.join(current_dir, "..", "data_collector", "data", "ieee39_telemetry_dataset.csv"))

def validate_dataset():
    print("==================================================================")
    print("STARTING DATASET VALIDATION...")
    print(f"Target File: {dataset_path}")
    print("==================================================================")
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file does not exist at {dataset_path}")
        sys.exit(1)
        
    errors = 0
    warnings = 0
    
    with open(dataset_path, "r") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print("Error: Dataset file is empty.")
            sys.exit(1)
            
        expected_cols = 160
        if len(headers) != expected_cols:
            print(f"Error: Column count mismatch. Expected {expected_cols}, got {len(headers)}.")
            errors += 1
            
        row_count = 0
        labels_seen = set()
        nan_count = 0
        primary_physics_violations = 0
        
        valid_primary_labels = {"NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS"}
        isolated_labels = {"NON_CONVERGED", "BLACKOUT", "INVALID_STATE"}
        all_valid_labels = valid_primary_labels | isolated_labels
        
        for row_idx, row in enumerate(reader, start=2):
            row_count += 1
            if len(row) != expected_cols:
                print(f"Error: Row {row_idx} column count mismatch. Got {len(row)} instead of {expected_cols}.")
                errors += 1
                continue
                
            label = row[-1]
            labels_seen.add(label)
            
            if label not in all_valid_labels:
                print(f"Error: Row {row_idx} has invalid label '{label}'.")
                errors += 1
                
            # Parse vectors
            try:
                P = np.array([float(x) for x in row[3:42]])
                Q = np.array([float(x) for x in row[42:81]])
                V = np.array([float(x) for x in row[81:120]])
                theta = np.array([float(x) for x in row[120:159]])
            except ValueError as e:
                print(f"Error: Row {row_idx} contains non-numeric data: {e}")
                errors += 1
                continue
                
            # Global NaN/Inf check (not allowed in any sample)
            if np.any(np.isnan(V)) or np.any(np.isnan(theta)) or np.any(np.isnan(P)) or np.any(np.isnan(Q)):
                nan_count += 1
                errors += 1
            if np.any(np.isinf(V)) or np.any(np.isinf(theta)) or np.any(np.isinf(P)) or np.any(np.isinf(Q)):
                nan_count += 1
                errors += 1
                
            # Physics verification on primary labels
            if label in valid_primary_labels:
                is_phys_valid, reasons = validate_physics(P, Q, V, theta)
                if not is_phys_valid:
                    primary_physics_violations += 1
                    print(f"Error: Row {row_idx} labeled '{label}' violates physics checks: {reasons}")
                    errors += 1
                    
        if row_count < 10000:
            print(f"Error: Dataset size {row_count} is too small. Expected at least 10000.")
            errors += 1
        else:
            print(f"Pass: Dataset has {row_count} rows (>= 10000 target).")
            
        missing_primary = valid_primary_labels - labels_seen
        if missing_primary:
            print(f"Error: Missing primary labels in dataset: {missing_primary}")
            errors += 1
        else:
            print("Pass: All 8 target primary labels are present in dataset.")
            
        # Check counts
        if nan_count > 0:
            print(f"Error: Found {nan_count} rows with NaN/Inf values.")
        if primary_physics_violations > 0:
            print(f"Error: Found {primary_physics_violations} primary label rows violating physics bounds.")
            
    print("==================================================================")
    print(f"VALIDATION COMPLETED. Errors: {errors}, Warnings: {warnings}")
    print("==================================================================")
    
    if errors > 0:
        print("Dataset Validation: FAILED")
        sys.exit(1)
    else:
        print("Dataset Validation: SUCCESS!")
        sys.exit(0)

if __name__ == "__main__":
    validate_dataset()
