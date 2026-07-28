import os
import csv
import sys
import numpy as np
from physics_validator import validate_physics

# Get dataset path
current_dir = os.path.dirname(os.path.abspath(__file__))
dataset_path = os.path.abspath(os.path.join(current_dir, "..", "data_collector", "data", "ieee39_telemetry_dataset.csv"))

def run_audit():
    print("==================================================================")
    print("STARTING DATASET AUDIT...")
    print(f"Target File: {dataset_path}")
    print("==================================================================")
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file does not exist at {dataset_path}")
        sys.exit(1)
        
    total_samples = 0
    valid_samples = 0
    invalid_samples = 0
    
    reason_counts = {}
    label_status = {}
    
    valid_labels = {"NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS"}
    
    with open(dataset_path, "r") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print("Error: Dataset file is empty.")
            sys.exit(1)
            
        for row_idx, row in enumerate(reader, start=2):
            if len(row) != 160:
                reason = "Column count mismatch (not 160)"
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                invalid_samples += 1
                continue
                
            total_samples += 1
            label = row[-1]
            
            # Parse metrics
            try:
                P = np.array([float(x) for x in row[3:42]])
                Q = np.array([float(x) for x in row[42:81]])
                V = np.array([float(x) for x in row[81:120]])
                theta = np.array([float(x) for x in row[120:159]])
            except ValueError as e:
                reason = f"Non-numeric fields: {e}"
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                invalid_samples += 1
                continue
                
            # Perform physics validation
            is_phys_valid, reasons = validate_physics(P, Q, V, theta)
            
            # Label checks
            is_valid_label = label in valid_labels
            
            if is_phys_valid and is_valid_label:
                valid_samples += 1
                label_status[label] = label_status.get(label, 0) + 1
            else:
                invalid_samples += 1
                if not is_valid_label:
                    reason = f"Invalid/Isolated label '{label}'"
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                for r in reasons:
                    reason_counts[r] = reason_counts.get(r, 0) + 1
                    
    print("\n--- AUDIT RESULTS ---")
    print(f"Total Samples Audited : {total_samples}")
    print(f"Total Valid Samples   : {valid_samples} ({valid_samples/total_samples*100:.2f}%)")
    print(f"Total Invalid Samples : {invalid_samples} ({invalid_samples/total_samples*100:.2f}%)")
    
    print("\n--- VALID SAMPLES BY LABEL ---")
    print(f"{'Label':<25} | {'Count':<8}")
    print("-" * 38)
    for lbl in sorted(valid_labels):
        print(f"{lbl:<25} | {label_status.get(lbl, 0):<8}")
        
    print("\n--- INVALID SAMPLE REASONS AND VIOLATIONS ---")
    if reason_counts:
        print(f"{'Reason for Failure':<60} | {'Occurrences':<10}")
        print("-" * 75)
        for r, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{r:<60} | {count:<10}")
    else:
        print("None. All samples meet validation guidelines.")
        
    print("==================================================================")

if __name__ == "__main__":
    run_audit()
