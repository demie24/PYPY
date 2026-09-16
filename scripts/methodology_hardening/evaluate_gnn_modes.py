#!/usr/bin/env python3
"""Evaluate the committed GNN checkpoint as raw model and legacy hybrid."""

from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "core" / "gnn"), str(ROOT / "core" / "digital_twin")]
from core.digital_twin.grid_topology import GridTopology
from core.gnn.gnn_evaluator import evaluate_gnn_performance, LABEL_MAP
from core.gnn.gnn_model import IEEE39GNN
from core.gnn.gnn_trainer import compute_vectorized_flows, extract_network_parameters


def main():
    df = pd.read_csv(ROOT / "core/data_collector/data/ieee39_telemetry_dataset.csv")
    df = df[~df.label.isin(["NON_CONVERGED", "BLACKOUT", "INVALID_STATE"])].copy().reset_index(drop=True)
    p = np.stack([df[f"bus_{i}_P"].to_numpy() / 100 for i in range(1, 40)], axis=1)
    q = np.stack([df[f"bus_{i}_Q"].to_numpy() / 100 for i in range(1, 40)], axis=1)
    v = np.stack([df[f"bus_{i}_V"].to_numpy() for i in range(1, 40)], axis=1)
    angle = np.stack([df[f"bus_{i}_theta"].to_numpy() for i in range(1, 40)], axis=1)
    labels = df.label.map(LABEL_MAP).to_numpy(np.int64)
    topology = GridTopology(); edge_index, params = extract_network_parameters(topology)
    pf, qf, loading = compute_vectorized_flows(v, angle, params)
    line = np.zeros((len(df), 46)); trafo = np.zeros((len(df), 46))
    line[:, ~params["is_trafo"]] = 1; trafo[:, params["is_trafo"]] = 1
    nodes = np.stack([p, q, v, angle], axis=-1).astype(np.float32)
    edges = np.stack([pf, qf, loading / 100, line, trafo], axis=-1).astype(np.float32)
    node_risk = np.zeros((len(df), 39), np.float32)
    edge_risk = np.clip(loading / 100, 0, 1).astype(np.float32)
    for row in range(len(df)):
        for bus in range(39):
            adjacent = params["adj_lists"][bus]
            maximum = np.max(loading[row, adjacent]) if adjacent else 0
            node_risk[row, bus] = np.clip(5 * abs(v[row, bus] - 1) + .1 * maximum / 100, 0, 1)
    rng = np.random.RandomState(42); order = rng.permutation(len(df)); cut = int(.85 * len(df)); test = order[cut:]
    loader = DataLoader(TensorDataset(torch.tensor(nodes[test]), torch.tensor(edges[test]), torch.tensor(labels[test]),
                        torch.tensor(node_risk[test]), torch.tensor(edge_risk[test])), batch_size=128)
    model = IEEE39GNN(edge_index=edge_index)
    model.load_state_dict(torch.load(ROOT / "core/gnn/trained_gnn_model.pt", map_location="cpu", weights_only=True))
    out = ROOT / "evaluation/methodology_hardening"; out.mkdir(parents=True, exist_ok=True)
    raw = evaluate_gnn_performance(model, loader, postprocess_mode="raw")
    legacy = evaluate_gnn_performance(model, loader, postprocess_mode="legacy")
    (out / "gnn_raw_evaluation.json").write_text(json.dumps(raw, indent=2) + "\n")
    (out / "gnn_postprocessed_evaluation.json").write_text(json.dumps(legacy, indent=2) + "\n")
    comparison = {"raw_accuracy": raw["accuracy"], "legacy_accuracy": legacy["accuracy"],
                  "raw_f1_macro": raw["f1_macro"], "legacy_f1_macro": legacy["f1_macro"],
                  "predictions_changed_by_legacy_heuristic": legacy["prediction_difference_count"]}
    (out / "gnn_evaluation_comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__": main()
