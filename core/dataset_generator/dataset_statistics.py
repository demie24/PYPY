import os
import csv
import numpy as np

# Get dataset path
current_dir = os.path.dirname(os.path.abspath(__file__))
dataset_path = os.path.abspath(os.path.join(current_dir, "..", "data_collector", "data", "ieee39_telemetry_dataset.csv"))

def compute_statistics():
    print("==================================================================")
    print("COMPUTING EXPANDED DATASET STATISTICS...")
    print(f"Target File: {dataset_path}")
    print("==================================================================")
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file does not exist at {dataset_path}")
        return
        
    labels = []
    scen_types = []
    
    all_V = []
    all_P = []
    all_Q = []
    all_theta = []
    
    label_groups = {}
    
    with open(dataset_path, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        for row in reader:
            if len(row) != 160:
                continue
                
            label = row[-1]
            scen_type = row[2]
            labels.append(label)
            scen_types.append(scen_type)
            
            P_vals = [float(val) for val in row[3:42]]
            Q_vals = [float(val) for val in row[42:81]]
            V_vals = [float(val) for val in row[81:120]]
            theta_vals = [float(val) for val in row[120:159]]
            
            all_P.append(P_vals)
            all_Q.append(Q_vals)
            all_V.append(V_vals)
            all_theta.append(theta_vals)
            
            if label not in label_groups:
                label_groups[label] = {
                    "P": [], "Q": [], "V": [], "theta": []
                }
            label_groups[label]["P"].append(P_vals)
            label_groups[label]["Q"].append(Q_vals)
            label_groups[label]["V"].append(V_vals)
            label_groups[label]["theta"].append(theta_vals)
            
    total_samples = len(labels)
    if total_samples == 0:
        print("No samples found in the dataset.")
        return
        
    print(f"Total Telemetry Samples: {total_samples}")
    print("\n--- 1. SCENARIO AND LABEL DISTRIBUTIONS ---")
    
    label_counts = {}
    for l in labels:
        label_counts[l] = label_counts.get(l, 0) + 1
        
    scen_type_counts = {}
    for st in scen_types:
        scen_type_counts[st] = scen_type_counts.get(st, 0) + 1
        
    print(f"{'Label':<25} | {'Count':<8} | {'Percentage':<10}")
    print("-" * 50)
    for lbl, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_samples) * 100
        print(f"{lbl:<25} | {count:<8} | {pct:>8.2f}%")
        
    print("\n" + f"{'Scenario Type':<25} | {'Count':<8} | {'Percentage':<10}")
    print("-" * 50)
    for st, count in sorted(scen_type_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_samples) * 100
        print(f"{st:<25} | {count:<8} | {pct:>8.2f}%")
        
    np_P = np.array(all_P)
    np_Q = np.array(all_Q)
    np_V = np.array(all_V)
    np_theta = np.array(all_theta)
    
    print("\n--- 2. GLOBAL STATE VARIABLE STATS ---")
    print(f"{'Metric':<10} | {'Voltage (pu)':<15} | {'Active Power (MW)':<18} | {'Reactive Power (MVar)':<22} | {'Angle (rad)':<12}")
    print("-" * 85)
    print(f"{'Min':<10} | {np.min(np_V):>15.4f} | {np.min(np_P):>18.2f} | {np.min(np_Q):>22.2f} | {np.min(np_theta):>12.4f}")
    print(f"{'Max':<10} | {np.max(np_V):>15.4f} | {np.max(np_P):>18.2f} | {np.max(np_Q):>22.2f} | {np.max(np_theta):>12.4f}")
    print(f"{'Mean':<10} | {np.mean(np_V):>15.4f} | {np.mean(np_P):>18.2f} | {np.mean(np_Q):>22.2f} | {np.mean(np_theta):>12.4f}")
    print(f"{'Std Dev':<10} | {np.std(np_V):>15.4f} | {np.std(np_P):>18.2f} | {np.std(np_Q):>22.2f} | {np.std(np_theta):>12.4f}")
    
    print("\n--- 3. VOLTAGE PROFILES BY EVENT LABEL ---")
    print(f"{'Label/Class':<25} | {'Min V (pu)':<12} | {'Max V (pu)':<12} | {'Mean V (pu)':<12} | {'Std V (pu)':<10}")
    print("-" * 75)
    for lbl in sorted(label_groups.keys()):
        v_arr = np.array(label_groups[lbl]["V"])
        print(f"{lbl:<25} | {np.min(v_arr):>12.4f} | {np.max(v_arr):>12.4f} | {np.mean(v_arr):>12.4f} | {np.std(v_arr):>10.4f}")
        
    print("\n--- 4. ACTIVE POWER INJECTIONS BY EVENT LABEL ---")
    print(f"{'Label/Class':<25} | {'Min P (MW)':<12} | {'Max P (MW)':<12} | {'Mean P (MW)':<12} | {'Std P (MW)':<10}")
    print("-" * 75)
    for lbl in sorted(label_groups.keys()):
        p_arr = np.array(label_groups[lbl]["P"])
        print(f"{lbl:<25} | {np.min(p_arr):>12.2f} | {np.max(p_arr):>12.2f} | {np.mean(p_arr):>12.2f} | {np.std(p_arr):>10.2f}")
        
    print("==================================================================")

if __name__ == "__main__":
    compute_statistics()
