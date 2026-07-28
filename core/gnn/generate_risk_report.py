import os
import sys
import json
import numpy as np
import pandas as pd
import torch

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

from graph_detector import GraphAnomalyDetector

def generate_risk_report(dataset_path: str):
    print("Generating Topology Risk Report...")
    
    # 1. Initialize detector (which loads the GNN model)
    detector = GraphAnomalyDetector()
    
    # 2. Extract structural critical components
    structural_buses = detector.analyzer.critical_nodes(top_n=5)
    structural_lines = detector.analyzer.critical_lines(top_n=5)
    
    # 3. Load dataset to compute class-specific dynamic risks
    df = pd.read_csv(dataset_path)
    exclude_labels = ["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"]
    df_valid = df[~df["label"].isin(exclude_labels)].copy()
    
    classes = ["NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS"]
    scenario_reports = {}
    
    # Node features column lists
    P_cols = [f"bus_{i}_P" for i in range(1, 40)]
    Q_cols = [f"bus_{i}_Q" for i in range(1, 40)]
    V_cols = [f"bus_{i}_V" for i in range(1, 40)]
    theta_cols = [f"bus_{i}_theta" for i in range(1, 40)]
    
    for cls in classes:
        df_cls = df_valid[df_valid["label"] == cls]
        if len(df_cls) == 0:
            continue
            
        print(f"Analyzing scenario class: {cls}...")
        
        # Take mean state representing this class
        P_mean = df_cls[P_cols].mean().values / 100.0
        Q_mean = df_cls[Q_cols].mean().values / 100.0
        V_mean = df_cls[V_cols].mean().values
        theta_mean = df_cls[theta_cols].mean().values
        
        node_feats = np.stack([P_mean, Q_mean, V_mean, theta_mean], axis=-1).astype(np.float32)
        
        # Run inference
        node_risks, edge_risks = detector.risk_scores(node_feats)
        critical_buses, critical_lines = detector.critical_components(node_feats, top_n=5)
        
        # Calculate propagation example: path from bus 30 (slack gen) to bus 15 (load center)
        prop_path = detector.propagation_prediction(30, 15)
        
        scenario_reports[cls] = {
            "average_node_risk": float(np.mean(node_risks)),
            "average_edge_risk": float(np.mean(edge_risks)),
            "max_node_risk": float(np.max(node_risks)),
            "max_edge_risk": float(np.max(edge_risks)),
            "critical_buses": critical_buses,
            "critical_lines": critical_lines,
            "sample_propagation_path_30_to_15": prop_path
        }
        
    report = {
        "title": "IEEE 39-Bus Grid Topology Risk Analysis Report",
        "structural_analysis": {
            "top_critical_buses_betweenness": structural_buses,
            "top_critical_lines_betweenness": structural_lines
        },
        "scenario_dynamic_analysis": scenario_reports
    }
    
    report_save_path = os.path.join(current_dir, "topology_risk_report.json")
    with open(report_save_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Topology risk report generated and saved to: {report_save_path}")
    return report

if __name__ == "__main__":
    dataset_path = os.path.join(parent_dir, "data_collector", "data", "ieee39_telemetry_dataset.csv")
    generate_risk_report(dataset_path)
