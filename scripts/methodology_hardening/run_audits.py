#!/usr/bin/env python3
"""Generate machine-readable methodology-hardening evidence without mutation."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core" / "pinn"))
from core.ai_training.temporal_split import chronological_label_partitions, overlap_report, window_spans
from core.pinn.physics_loss import IEEE39PhysicsLoss
from core.pinn.pinn_model import IEEE39PINNAutoencoder

OUT = ROOT / "evaluation" / "methodology_hardening"
DATASET = ROOT / "core" / "data_collector" / "data" / "ieee39_telemetry_dataset.csv"
VALID_LABELS = ("NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(name: str, value: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def old_random_spans(n: int, sequence_length: int, horizon: int = 0):
    width = sequence_length + horizon
    spans = [np.arange(i, i + width) for i in range(n - width + 1)]
    rng = np.random.RandomState(42)
    order = rng.permutation(len(spans)); a = int(.70 * len(spans)); b = a + int(.15 * len(spans))
    return {"train": [spans[i] for i in order[:a]], "validation": [spans[i] for i in order[a:b]], "test": [spans[i] for i in order[b:]]}


def temporal_audit(df: pd.DataFrame) -> None:
    valid = df[df.label.isin(VALID_LABELS)].copy().reset_index(drop=True)
    partitions = chronological_label_partitions(valid)
    report = {"schema_version": "pypy.temporal-overlap.v1", "dataset_sha256": sha256(DATASET), "models": {}}
    for model, length, horizon in (("lstm", 20, 0), ("stgnn", 20, 5)):
        corrected = {name: window_spans(part.raw_indices, length, horizon) for name, part in partitions.items()}
        report["models"][model] = {
            "original_random_window_split": overlap_report(old_random_spans(len(valid), length, horizon)),
            "corrected_chronological_label_block_split": overlap_report(corrected),
            "correction": "split each contiguous label block chronologically before constructing windows",
            "scenario_id_grouping_rejected": "scenario_id is unique per row and cannot identify simulation runs",
        }
    write("temporal_overlap_report.json", report)


def dataset_audit(df: pd.DataFrame) -> None:
    schema = json.dumps([{"name": c, "dtype": str(df[c].dtype)} for c in df.columns], separators=(",", ":"))
    features = [c for c in df.columns if c.startswith("bus_")]
    manifest = {
        "schema_version": "pypy.dataset-manifest.v1", "path": str(DATASET.relative_to(ROOT)),
        "sha256": sha256(DATASET), "rows": len(df), "columns": len(df.columns),
        "schema_sha256": hashlib.sha256(schema.encode()).hexdigest(),
        "timestamp_min": int(df.timestamp.min()), "timestamp_max": int(df.timestamp.max()),
        "label_distribution": dict(sorted(Counter(df.label).items())),
    }
    write("dataset_manifest.json", manifest)
    valid = df[df.label.isin(VALID_LABELS)]
    feature_duplicates = int(valid.duplicated(subset=features).sum())
    integrity = {
        "schema_version": "pypy.dataset-integrity.v1",
        "full_row_duplicates": int(df.duplicated().sum()), "valid_feature_duplicates": feature_duplicates,
        "nonfinite_feature_values": int(np.count_nonzero(~np.isfinite(valid[features].to_numpy(float)))),
        "class_counts": dict(sorted(Counter(valid.label).items())),
        "class_balanced": len(set(Counter(valid.label).values())) == 1,
        "label_columns_in_features": False, "scenario_id_in_model_features": False, "timestamp_in_model_features": False,
        "scalers_fit_after_split": True,
        "known_threats": [
            "LSTM/ST-GNN legacy windows overlapped across partitions.",
            "REPLAY rows can duplicate NORMAL feature states by design.",
            "GNN legacy evaluator changed NORMAL/REPLAY predictions using a seeded heuristic.",
        ],
    }
    write("dataset_integrity.json", integrity)


def physics_flags(rows: np.ndarray, physics: IEEE39PhysicsLoss) -> tuple[dict, dict]:
    counts = Counter(); residuals = []
    for row in rows:
        p, q, v, angle = np.split(row, 4)
        voltage = bool(np.any((v < .85) | (v > 1.15)))
        theta = bool(np.any((angle < -np.pi) | (angle > np.pi)))
        vc = v * np.exp(1j * angle); s = vc * np.conj(physics.Y_bus @ vc)
        p_res = float(np.mean(np.abs(p / 100.0 + s.real)))
        q_res = float(np.mean(np.abs(q / 100.0 + s.imag)))
        flags = {"voltage": voltage, "angle": theta, "active_power_balance": p_res > .05, "reactive_power_balance": q_res > .05}
        counts.update(k for k, value in flags.items() if value); counts["any"] += int(any(flags.values()))
        residuals.append((p_res, q_res))
    n = len(rows); residuals = np.asarray(residuals)
    return ({key: {"samples": int(counts[key]), "rate": float(counts[key] / n)} for key in (*flags, "any")},
            {"active_mean": float(residuals[:, 0].mean()), "reactive_mean": float(residuals[:, 1].mean()),
             "active_median": float(np.median(residuals[:, 0])), "reactive_median": float(np.median(residuals[:, 1]))})


def pinn_audit(df: pd.DataFrame) -> None:
    columns = sum(([f"bus_{i}_{x}" for i in range(1, 40)] for x in ("P", "Q", "V", "theta")), [])
    valid = df[df.label.isin(VALID_LABELS)].copy().reset_index(drop=True)
    data = valid[columns].to_numpy(np.float32)
    rng = np.random.RandomState(42); idx = rng.permutation(len(data)); test_idx = idx[int(.85 * len(data)):]
    model = IEEE39PINNAutoencoder(); checkpoint = ROOT / "core" / "pinn" / "trained_pinn_model.pt"
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)); model.eval()
    with torch.no_grad(): reconstruction = model(torch.tensor(data[test_idx]))[0].numpy()
    physics = IEEE39PhysicsLoss()
    gt_counts, gt_residuals = physics_flags(data[test_idx], physics)
    pred_counts, pred_residuals = physics_flags(reconstruction, physics)
    per_label = {}
    for label in VALID_LABELS:
        subset = valid[valid.label == label][columns].to_numpy(np.float32)
        with torch.no_grad(): pred = model(torch.tensor(subset))[0].numpy()
        gc, _ = physics_flags(subset, physics); pc, _ = physics_flags(pred, physics)
        per_label[label] = {"ground_truth": gc, "pinn_reconstruction": pc}
    write("pinn_physics_audit.json", {
        "schema_version": "pypy.pinn-physics-audit.v1", "checkpoint_sha256": sha256(checkpoint),
        "test_samples": len(test_idx), "thresholds": {"voltage_pu": [.85, 1.15], "angle_rad": [-float(np.pi), float(np.pi)], "mean_p_mismatch_pu": .05, "mean_q_mismatch_pu": .05},
        "ground_truth": {"violations": gt_counts, "residuals": gt_residuals},
        "pinn_reconstruction": {"violations": pred_counts, "residuals": pred_residuals},
        "per_label_full_dataset": per_label,
        "classification": ["model_physics_consistency_failure", "fixed_topology_metric_invalid_for_topology-changing N-1/N-2 states"],
        "conclusion": "The 1.0 reconstruction violation rate is genuine at the implemented 0.05 pu threshold even for nominal states; ground-truth nominal states pass. Ground-truth topology-changing states also fail because the checker uses the intact Y-bus.",
    })


def unit_audit() -> None:
    write("current_unit_audit.json", {
        "schema_version": "pypy.current-unit-audit.v1",
        "finding": "current_pu is a legacy misnomer containing pandapower kA in the IEEE-39 runtime",
        "conversion": "current_loading_pu = current_ka / 3.0 legacy engineering capacity",
        "stages": [
            {"stage": "pandapower", "variable": "res_line.i_ka/res_trafo.i_hv_ka", "unit": "kA"},
            {"stage": "GridACSolver", "variable": "line_flows.current", "unit": "kA"},
            {"stage": "Digital Twin", "variable": "current_ka", "unit": "kA", "status": "canonical"},
            {"stage": "MQTT compatibility", "variable": "current_pu", "unit": "kA", "status": "deprecated alias"},
            {"stage": "MQTT normalised", "variable": "current_loading_pu", "unit": "per-unit of 3.0 kA legacy capacity"},
            {"stage": "physics/TRUST", "variable": "current_ka with current_pu fallback", "unit": "kA", "used_as": "measurement/stability"},
            {"stage": "recovery", "variable": "capacity_pct/current_ka", "unit": "percent/kA", "used_as": "thermal gate"},
            {"stage": "training CSV", "variable": "none", "unit": "not applicable", "used_as": "models derive graph flows from P/Q/V/angle"},
        ],
        "backward_compatibility": "current_pu retained; new consumers must prefer current_ka/current_loading_pu",
    })


def package_version(name: str):
    try: return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: return "NOT_INSTALLED"


def command(args):
    try: return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc: return f"NOT_VERIFIED: {exc}"


def environment_audit() -> None:
    packages = {name: package_version(name) for name in ("numpy", "pandas", "scipy", "pandapower", "torch", "fastapi", "paho-mqtt")}
    freeze = command([sys.executable, "-m", "pip", "freeze"])
    write("environment_manifest.json", {
        "schema_version": "pypy.environment.v1", "python": platform.python_version(), "platform": platform.platform(),
        "packages": packages, "pip_freeze_sha256": hashlib.sha256(freeze.encode()).hexdigest(), "pip_freeze": freeze.splitlines(),
        "docker": command(["docker", "--version"]), "docker_compose": command(["docker", "compose", "version"]),
        "compose_images": {"postgres": "postgres:15-alpine", "redis": "redis:7-alpine", "mosquitto": "eclipse-mosquitto:latest", "node": "node:18-alpine", "dashboard_server": "nginx:1.23-alpine"},
        "frontend": {"react": "^18.2.0", "vite": "^5.0.0"},
        "limitations": ["pip ranges are not a lock file", "Mosquitto latest is not digest-pinned", "host manifest may differ from container-resolved packages"],
    })


def rl_audit() -> None:
    rows = []
    for kind, rel in (("PPO", "checkpoints/ppo_self_healing.pt"), ("DQN", "checkpoints/dqn_self_healing.pt")):
        path = ROOT / rel
        rows.append({"policy": kind, "path": rel, "sha256": sha256(path), "size_bytes": path.stat().st_size,
                     "state_dimension": 72, "action_dimension": 10,
                     "training_script": "core/self_healing/rl/rl_trainer.py",
                     "environment": "core/self_healing/rl_environment.py (legacy/self-healing environment)",
                     "training_episode_count": "NOT_VERIFIED", "seed": "NOT_VERIFIED",
                     "native_ieee39_training": False,
                     "git_history": command(["git", "log", "--follow", "--format=%h %ad %s", "--date=iso", "--", rel]).splitlines()})
    write("rl_checkpoint_provenance.json", {"schema_version": "pypy.rl-provenance.v1", "checkpoints": rows,
        "thesis_wording": "Existing PPO and DQN policies were integrated as recovery proposal mechanisms through a deterministic 72-element compatibility encoder."})


def semantic_audits() -> None:
    write("attack_metadata_dependency.json", {"schema_version": "pypy.attack-metadata.v1", "components": {
        "autoencoder": {"metadata": "grid/attack control", "effect": "confirmation window/cooldown", "blind_mode": "ignores metadata"},
        "lstm": {"metadata": None, "inputs": "telemetry only"}, "gnn": {"metadata": None, "inputs": "telemetry only"},
        "stgnn": {"metadata": None, "inputs": "telemetry only"}, "pinn": {"metadata": None, "inputs": "telemetry only"},
        "fusion": {"metadata": "attack_status", "effect": "nominal calibration exclusion only"},
        "physics": {"metadata": "attack_status", "effect": "residual calibration exclusion only"},
        "trust": {"metadata": None, "inputs": "physics and AI evidence"},
        "threat": {"metadata": "attack_status/compromised_nodes", "effect": "direct score/confidence/affected-node contribution", "blind_mode": "metadata removed"},
        "recovery": {"metadata": None, "inputs": "telemetry/fusion/trust/threat/physics"}},
        "modes": {"blind": "DEFENCE_EVALUATION_MODE=blind", "experiment_aware": "DEFENCE_EVALUATION_MODE=experiment_aware"}})
    write("detection_terminology.json", {"schema_version": "pypy.detection-terminology.v1", "components": {
        "autoencoder": ["anomaly_detection", "localisation", "heuristic_diagnosis"], "lstm": ["attack_and_contingency_classification", "temporal_anomaly_score"],
        "gnn": ["snapshot_classification", "node_localisation", "branch_localisation"], "stgnn": ["future_node_and_branch_risk_prediction"],
        "pinn": ["reconstruction", "physics_consistency_assessment"], "fusion": ["evidence_aggregation"],
        "TRUST": ["rule_based_trust_assessment"], "threat_scorer": ["rule_based_threat_scoring"]}})
    write("training_reproducibility.json", {"schema_version": "pypy.training-reproducibility.v1", "models": {
        "LSTM": {"python_seed": "NOT_SET", "numpy_split_seed": 42, "torch_seed_hardened": 42, "dataloader_shuffle": True, "dataloader_generator_seed_hardened": 42, "cuda_determinism": "NOT_APPLICABLE_TO_CPU_RUN"},
        "GNN": {"python_seed": "NOT_SET", "numpy_split_seed": 42, "torch_seed": "NOT_SET_IN_LEGACY_TRAINER", "dataloader_shuffle": True, "level": "split reproducible; weights not guaranteed"},
        "ST-GNN": {"python_seed": "NOT_SET", "numpy_split_seed": 42, "torch_seed_hardened": 42, "dataloader_shuffle": True, "dataloader_generator_seed_hardened": 42, "cuda_determinism": "NOT_APPLICABLE_TO_CPU_RUN"},
        "PINN": {"python_seed": "NOT_SET", "numpy_split_seed": 42, "torch_seed": "NOT_SET", "dataloader_shuffle": True, "level": "split reproducible; weights not guaranteed"}},
        "recommendation": "Use the deterministic CPU thesis configuration and record checkpoint hashes; do not claim bitwise GPU reproducibility."})
    write("common_held_out_analysis.json", {"schema_version": "pypy.common-held-out.v1",
        "feasible": True, "partition_unit": "chronological blocks within each label",
        "snapshot_models": ["GNN", "PINN"], "temporal_models": ["LSTM", "ST-GNN"],
        "alignment": "All models can use the same raw train/validation/test row blocks; temporal windows are then constructed only inside their partition.",
        "non_comparable_targets": {"LSTM": "eight-class classification", "GNN": "classification and spatial risks", "ST-GNN": "future risks", "PINN": "reconstruction and physics consistency"},
        "warning": "Shared partitions strengthen comparison but do not make model metrics interchangeable."})
    write("ablation_decision.json", {"schema_version": "pypy.ablation-decision.v1", "decision": "DO_NOT_PRESENT_AS_COMPLETED",
        "reason": "No aligned stored component-output dataset exists for a controlled causal ablation, and disabling safety gates would not measure policy quality.",
        "thesis_action": "Remove ablation experiments from Chapter 3 or label a future leave-one-model-out fusion experiment as proposed work.",
        "diploma_scope": "optional"})


def corrected_model_comparisons() -> None:
    old_lstm = json.loads((ROOT / "core/lstm/evaluation_results.json").read_text())
    new_lstm = json.loads((OUT / "lstm_corrected/evaluation_results.json").read_text())
    lstm = {"schema_version": "pypy.corrected-lstm.v1", "split": "chronological label blocks before windows",
        "training_epochs": 15, "selected_window": 20, "production_checkpoint_overwritten": False,
        "original": old_lstm, "leakage_safe": new_lstm,
        "difference": {"accuracy": new_lstm["accuracy"] - old_lstm["accuracy"],
                       "f1_weighted": new_lstm["f1_weighted"] - old_lstm["f1_weighted"]}}
    write("lstm_corrected_evaluation.json", lstm)
    old_st = json.loads((ROOT / "core/gnn/stgnn_evaluation_results.json").read_text())
    new_st = json.loads((OUT / "stgnn_corrected/stgnn_evaluation_results.json").read_text())
    stgnn = {"schema_version": "pypy.corrected-stgnn.v1", "split": "chronological label blocks before windows",
        "training_epochs": 5, "legacy_training_epochs": 20, "production_checkpoint_overwritten": False,
        "qualification": "Leakage-safe audit checkpoint used five CPU epochs because the Python edge-loop implementation required about 2.5 minutes per epoch. Compare directionally; this is not a controlled same-budget superiority test.",
        "original": old_st, "leakage_safe": new_st}
    write("stgnn_corrected_evaluation.json", stgnn)


def main():
    df = pd.read_csv(DATASET)
    dataset_audit(df); temporal_audit(df); pinn_audit(df); unit_audit(); environment_audit(); rl_audit(); semantic_audits()
    if (OUT / "lstm_corrected/evaluation_results.json").exists() and (OUT / "stgnn_corrected/stgnn_evaluation_results.json").exists():
        corrected_model_comparisons()
    print(OUT)


if __name__ == "__main__": main()
