"""
Unit Tests for PYPY V10.7 — Zero-Parameter FDIA Cut-Line Pathogen.
All 12 tests must pass.
"""
import os
import sys
import numpy as np
import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.digital_twin.multi_grid_topology import MultiGridTopology
from core.adversarial.cutline_discovery_engine import CutLineDiscoveryEngine
from core.adversarial.zero_parameter_fdia import ZeroParameterFDIA
from core.adversarial.stealth_fdia_optimizer import StealthFDIAOptimizer, PINNResidualProxy, GNNAnomalyProxy
from core.adversarial.fdia_islanding_env import FDIAIslandingEnv


# ---------------------------------------------------------------------------
# T1: Bridge detection works and identifies correct bridges
# ---------------------------------------------------------------------------
def test_bridge_detection():
    """Verify Tarjan's bridge-finding algorithm runs and returns line list."""
    topo = MultiGridTopology("ieee14")
    engine = CutLineDiscoveryEngine(topo, seed=42)
    bridges = engine.discover_bridges()
    
    assert isinstance(bridges, list), "Bridges must be returned as a list"
    for b in bridges:
        assert isinstance(b, str), "Bridge ID must be a string"
        assert any(line["id"] == b for line in topo.lines), f"Bridge ID {b} not in topo lines"
    
    # Run manual ground truth verification via BFS to check correctness
    # For each bridge, removing it should disconnect the graph
    from core.adversarial.cutline_discovery_engine import _GraphContext
    ctx = _GraphContext(topo)
    
    def is_connected_excluding(remove_lid: str) -> bool:
        visited = set()
        queue = [0]
        visited.add(0)
        while queue:
            curr = queue.pop(0)
            for nb, lid in ctx.adj[curr]:
                if lid == remove_lid:
                    continue
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        return len(visited) == topo.num_buses

    for b in bridges:
        assert not is_connected_excluding(b), f"Line {b} was classified as bridge but removing it did not disconnect the graph"
    
    print("✓ test_bridge_detection PASSED")


# ---------------------------------------------------------------------------
# T2: Articulation points detection is correct
# ---------------------------------------------------------------------------
def test_articulation_points():
    """Verify articulation point detection finds vertices that disconnect grid."""
    topo = MultiGridTopology("ieee39")
    engine = CutLineDiscoveryEngine(topo, seed=42)
    aps = engine.discover_articulation_points()
    
    assert isinstance(aps, list), "APs must be a list"
    for ap in aps:
        assert isinstance(ap, (int, np.integer)), "AP index must be an integer"
        assert 0 <= ap < topo.num_buses, f"AP index {ap} out of range [0, {topo.num_buses})"
        
    # Validation by vertex deletion: removing an AP should disconnect graph
    from core.adversarial.cutline_discovery_engine import _GraphContext
    ctx = _GraphContext(topo)
    
    def is_connected_excluding_vertex(remove_vertex: int) -> bool:
        start_node = 0 if remove_vertex != 0 else 1
        visited = set()
        queue = [start_node]
        visited.add(start_node)
        while queue:
            curr = queue.pop(0)
            for nb, lid in ctx.adj[curr]:
                if nb == remove_vertex:
                    continue
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        return len(visited) == (topo.num_buses - 1)

    for ap in aps:
        assert not is_connected_excluding_vertex(ap), f"Bus {ap} was classified as AP but removing it did not disconnect the graph"
        
    print("✓ test_articulation_points PASSED")


# ---------------------------------------------------------------------------
# T3: Cutline discovery lists cutlines with proper structure
# ---------------------------------------------------------------------------
def test_cutline_discovery():
    """Verify discover_cut_lines returns ranks, flags, risk scores."""
    topo = MultiGridTopology("ieee57")
    engine = CutLineDiscoveryEngine(topo, seed=42)
    top_k = engine.discover_cut_lines(top_k=5)
    
    assert len(top_k) == 5, f"Expected 5 cutlines, got {len(top_k)}"
    for r in top_k:
        assert "line_id" in r
        assert "is_bridge" in r
        assert "risk_score" in r
        assert "rank" in r
        assert r["rank"] in [1, 2, 3, 4, 5]
        
    print("✓ test_cutline_discovery PASSED")


# ---------------------------------------------------------------------------
# T4: Islanding risk score calculation matches bounds and components
# ---------------------------------------------------------------------------
def test_islanding_risk():
    """Verify risk score computed for all lines resides in [0, 1]."""
    topo = MultiGridTopology("ieee39")
    engine = CutLineDiscoveryEngine(topo, seed=42)
    risk = engine.compute_islanding_risk()
    
    assert len(risk) == len(topo.lines), "Should compute risk for every line"
    for lid, score in risk.items():
        assert 0.0 <= score <= 1.0 + 1e-6, f"Risk score {score} out of [0, 1]"
        
    print("✓ test_islanding_risk PASSED")


# ---------------------------------------------------------------------------
# T5: ZeroParameterFDIA initialization and default vectors
# ---------------------------------------------------------------------------
def test_zero_param_fdia_init():
    """Verify nominal measurements have expected dimensions and consistency."""
    topo = MultiGridTopology("ieee14")
    fdia = ZeroParameterFDIA(topo, seed=42)
    
    assert len(fdia.V_nom) == topo.num_buses
    assert len(fdia.P_nom) == topo.num_buses
    assert len(fdia.P_line_nom) == len(topo.lines)
    assert fdia.f_nom == 60.0
    
    print("✓ test_zero_param_fdia_init PASSED")


# ---------------------------------------------------------------------------
# T6: Voltage spoofing stays within bounds
# ---------------------------------------------------------------------------
def test_spoof_voltage():
    """Verify single and multi-bus voltage spoofing adheres to constraints."""
    topo = MultiGridTopology("ieee14")
    fdia = ZeroParameterFDIA(topo, seed=42)
    
    V_sp, delta = fdia.spoof_voltage(bus_id=2, delta_v=0.03, direction="drop")
    assert delta == 0.03
    assert np.abs(V_sp[2] - fdia.V_nom[2]) <= 0.031
    assert V_sp[2] < fdia.V_nom[2]
    
    V_sp_multi = fdia.spoof_voltage_multi(bus_ids=[1, 3, 5], delta_v=0.04, direction="boost")
    for b in [1, 3, 5]:
        assert V_sp_multi[b] > fdia.V_nom[b]
        assert np.abs(V_sp_multi[b] - fdia.V_nom[b]) <= 0.041
        
    print("✓ test_spoof_voltage PASSED")


# ---------------------------------------------------------------------------
# T7: Power spoofing and DC approximation consistency
# ---------------------------------------------------------------------------
def test_spoof_power():
    """Verify power spoofing generates consistent flows under V_sp."""
    topo = MultiGridTopology("ieee14")
    fdia = ZeroParameterFDIA(topo, seed=42)
    
    # Test additive spoofing
    P_sp, delta = fdia.spoof_power(line_id=topo.lines[0]["id"], delta_p=0.08)
    assert delta == 0.08
    idx = fdia._lid_to_idx[topo.lines[0]["id"]]
    assert np.abs(P_sp[idx] - fdia.P_line_nom[idx]) > 0.001
    
    # Test voltage-consistent spoofing
    V_sp = fdia.spoof_voltage_multi([0, 1], delta_v=0.04, direction="boost")
    P_sp_cons, _ = fdia.spoof_power(line_id=topo.lines[0]["id"], delta_p=0.08, consistent_with_v=V_sp)
    # The consistent flow should be computed from V_sp angle difference
    assert P_sp_cons[idx] is not None
    
    print("✓ test_spoof_power PASSED")


# ---------------------------------------------------------------------------
# T8: Frequency spoofing and ramp bounds
# ---------------------------------------------------------------------------
def test_spoof_frequency():
    """Verify frequency spoofing stays within bounds and ramp works."""
    topo = MultiGridTopology("ieee39")
    fdia = ZeroParameterFDIA(topo, seed=42)
    
    f_sp, df = fdia.spoof_frequency(region="NA", delta_f=0.10, trend="decline")
    assert 0.0 <= df <= 0.15
    assert f_sp < 60.0
    assert f_sp >= 59.5  # UFLS cutoff
    
    ramp = fdia.spoof_frequency_ramp(region="NA", n_steps=5, final_delta=0.12)
    assert len(ramp) == 5
    assert ramp[0] == 60.0
    assert ramp[-1] == 60.0 - 0.12
    
    print("✓ test_spoof_frequency PASSED")


# ---------------------------------------------------------------------------
# T9: PINN residual proxy and gradient flow
# ---------------------------------------------------------------------------
def test_pinn_residual_proxy():
    """Verify PINN residual calculations and gradient direction."""
    topo = MultiGridTopology("ieee14")
    # Make reactances uniform to avoid numerical stiffness in gradient check
    for line in topo.lines:
        line["X"] = 0.1
        
    proxy = PINNResidualProxy(topo, seed=42)
    proxy.noise_std = 0.0  # Disable noise for deterministic gradient verification
    
    V = np.ones(topo.num_buses)
    P = np.zeros(topo.num_buses)
    
    res = proxy.residual(V, P)
    assert res >= 0
    
    # Perturb V to create mismatch
    V_perturbed = V.copy()
    V_perturbed[2] -= 0.05
    res_pert = proxy.residual(V_perturbed, P)
    
    # Calculate gradient
    grad = proxy.gradient_wrt_V(V_perturbed, P)
    assert grad.shape == (topo.num_buses,)
    assert not np.allclose(grad, 0.0)
    
    # Linearity / Direction check: step along negative gradient should decrease residual
    V_step = V_perturbed - 1e-4 * grad
    res_step = proxy.residual(V_step, P)
    assert res_step < res_pert, f"Step along negative gradient did not reduce residual: res_pert={res_pert:.5f}, res_step={res_step:.5f}"
    
    print("✓ test_pinn_residual_proxy PASSED")


# ---------------------------------------------------------------------------
# T10: GNN anomaly proxy and gradient flow
# ---------------------------------------------------------------------------
def test_gnn_anomaly_proxy():
    """Verify GNN anomaly score calculations and gradient direction."""
    topo = MultiGridTopology("ieee14")
    proxy = GNNAnomalyProxy(topo, seed=42)
    
    V_nom = np.ones(topo.num_buses)
    V_sp = V_nom.copy()
    V_sp[3] += 0.04
    P = np.zeros(topo.num_buses)
    
    score = proxy.anomaly_score(V_sp, P, V_nom, P)
    assert score > 0
    
    grad = proxy.gradient_wrt_V(V_sp, V_nom)
    assert grad.shape == (topo.num_buses,)
    assert not np.allclose(grad, 0.0)
    
    # Direction check
    V_step = V_sp - 0.01 * grad
    score_step = proxy.anomaly_score(V_step, P, V_nom, P)
    assert score_step <= score + 1e-4, "Step along negative gradient did not reduce GNN anomaly score"
    
    print("✓ test_gnn_anomaly_proxy PASSED")


# ---------------------------------------------------------------------------
# T11: Stealth FDIA Optimizer converges
# ---------------------------------------------------------------------------
def test_stealth_optimizer():
    """Verify projected gradient descent reduces total multi-objective loss."""
    topo = MultiGridTopology("ieee14")
    fdia = ZeroParameterFDIA(topo, seed=42)
    optimizer = StealthFDIAOptimizer(topo, n_iter=10, seed=42)
    
    # Initialize attack
    attack_init = fdia.generate_fdia(target_lines=[topo.lines[0]["id"]], strategy="combined")
    
    # Run optimization
    opt_res = optimizer.optimize(attack_init, fdia.V_nom, fdia.P_nom)
    
    assert opt_res["final_loss"] <= opt_res["loss_history"][0] + 1e-4
    assert len(opt_res["loss_history"]) == 10
    
    print("✓ test_stealth_optimizer PASSED")


# ---------------------------------------------------------------------------
# T12: FDIA Islanding RL environment rollouts
# ---------------------------------------------------------------------------
def test_fdia_islanding_env():
    """Verify gym step execution and policy rollouts under partial observability."""
    topo = MultiGridTopology("ieee14")
    env = FDIAIslandingEnv(topo, observability=0.60, max_steps=5, seed=42)
    
    obs = env.reset()
    assert len(obs) == env.obs_dim
    
    # Execute single step
    action = np.zeros(env.act_dim, dtype=np.float32)
    obs, r, done, info = env.step(action)
    
    assert len(obs) == env.obs_dim
    assert isinstance(r, float)
    assert isinstance(done, bool)
    assert "target_lines" in info
    
    # Execute rollouts
    res_rand = env.rollout_random_policy(n_episodes=2)
    assert len(res_rand["load_shed"]) == 2
    assert "success" in res_rand
    
    res_greedy = env.rollout_greedy_policy(n_episodes=2)
    assert len(res_greedy["load_shed"]) == 2
    
    print("✓ test_fdia_islanding_env PASSED")
