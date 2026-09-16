#!/usr/bin/env python3
"""Run time.perf_counter benchmark for all 7 core PYPY pipeline components."""

import sys, time, json
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.lstm.lstm_model import IEEE39LSTMClassifier
from core.pinn.pinn_model import IEEE39PINNAutoencoder
from core.gnn.gnn_model import IEEE39GNN
from core.gnn.stgnn_model import IEEE39STGNN
from core.digital_twin.grid_topology import GridTopology
from core.gnn.gnn_trainer import extract_network_parameters
from core.threat_engine.scorer import ThreatScoringEngine
from core.orchestrator.ai_orchestrator import AIOrchestrator
from core.self_healing.restoration_sandbox import RestorationSandbox

def profile_fn(fn, iterations=50, warmup=5):
    for _ in range(warmup):
        fn()
    durations = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000.0) # ms
    arr = np.array(durations)
    return {
        'classification': 'MEASURED',
        'iterations': iterations,
        'mean_ms': round(float(np.mean(arr)), 4),
        'median_ms': round(float(np.median(arr)), 4),
        'min_ms': round(float(np.min(arr)), 4),
        'max_ms': round(float(np.max(arr)), 4),
        'std_ms': round(float(np.std(arr)), 4),
        'gpu_used': False
    }

def main():
    print("Profiling PYPY components with time.perf_counter()...")

    # 1. LSTM
    lstm = IEEE39LSTMClassifier()
    x_lstm = torch.randn(1, 20, 156)
    m_lstm = profile_fn(lambda: lstm(x_lstm))
    m_lstm['source'] = 'core/lstm/lstm_model.py::IEEE39LSTMClassifier'
    m_lstm['notes'] = 'Batch-1 sequence window W=20 x 156 CPU forward pass'

    # 2. GNN
    topology = GridTopology()
    edge_index, params = extract_network_parameters(topology)
    gnn = IEEE39GNN(edge_index=edge_index)
    nodes = torch.randn(39, 4)
    edges = torch.randn(46, 5)
    m_gnn = profile_fn(lambda: gnn(nodes, edges))
    m_gnn['source'] = 'core/gnn/gnn_model.py::IEEE39GNN'
    m_gnn['notes'] = 'IEEE 39-bus graph message-passing CPU forward pass'

    # 3. STGNN
    stgnn = IEEE39STGNN(edge_index=edge_index)
    seq_nodes = torch.randn(1, 20, 39, 4)
    seq_edges = torch.randn(1, 20, 46, 5)
    m_stgnn = profile_fn(lambda: stgnn(seq_nodes, seq_edges))
    m_stgnn['source'] = 'core/gnn/stgnn_model.py::IEEE39STGNN'
    m_stgnn['notes'] = 'Spatio-temporal sequence graph message-passing CPU forward pass'

    # 4. PINN
    pinn = IEEE39PINNAutoencoder()
    x_pinn = torch.randn(1, 156)
    m_pinn = profile_fn(lambda: pinn(x_pinn))
    m_pinn['source'] = 'core/pinn/pinn_model.py::IEEE39PINNAutoencoder'
    m_pinn['notes'] = 'Physics-informed autoencoder CPU forward pass'

    # 5. Threat Engine
    scorer = ThreatScoringEngine('blind')
    dummy_tel = {'bus_voltages': {'1': 1.0}, 'line_currents': {'1': 0.5}, 'breaker_states': {'1': 1}, 'active_powers': {'1': 10.0}, 'reactive_powers': {'1': 2.0}}
    m_threat = profile_fn(lambda: scorer.calculate_threat(dummy_tel))
    m_threat['source'] = 'core/threat_engine/scorer.py::ThreatScoringEngine'
    m_threat['notes'] = 'Multi-layer fusion and trust degradation scoring'

    # 6. AI Orchestrator
    orch = AIOrchestrator()
    m_orch = profile_fn(lambda: orch.evaluate_proposed_command('CLOSE', 'L_line_0', 'AI_RL_PPO_DQN_CONSENSUS'))
    m_orch['source'] = 'core/orchestrator/ai_orchestrator.py::AIOrchestrator'
    m_orch['notes'] = 'Multi-agent consensus and cooldown safety gate evaluation'

    # 7. Sandbox Dry Run
    sandbox = RestorationSandbox()
    target_breaker = next(iter(sandbox.breakers))
    m_sandbox = profile_fn(lambda: sandbox.dry_run_action("OPEN", target_breaker), iterations=20, warmup=2)
    m_sandbox['source'] = 'core/self_healing/restoration_sandbox.py::RestorationSandbox'
    m_sandbox['notes'] = 'Newton-Raphson AC powerflow dry-run rehearsal'

    result = {
        'generated_at_utc': '2026-08-19T07:45:00Z',
        'benchmark_method': 'time.perf_counter',
        'metrics': {
            'lstm_inference': m_lstm,
            'gnn_inference': m_gnn,
            'stgnn_inference': m_stgnn,
            'pinn_residual_evaluation': m_pinn,
            'threat_scoring': m_threat,
            'orchestrator_decision': m_orch,
            'restoration_sandbox_dry_run': m_sandbox
        },
        'not_measured': [],
        'warnings': []
    }

    out_file = ROOT / "evaluation/methodology_hardening/runtime_metrics_final.json"
    out_file.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Successfully exported runtime metrics to {out_file}")
    print(json.dumps(result['metrics'], indent=2))

if __name__ == "__main__":
    main()
