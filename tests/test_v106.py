"""
Unit Tests for PYPY V10.6 — Cross-Grid Transfer Learning Pathogen.
Target: 6/6 PASS.
"""
import os
import sys
import numpy as np
import pytest

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


# -----------------------------------------------------------------------
# Test 1: Multi-Grid Topology Loading
# -----------------------------------------------------------------------
def test_multi_grid_topology():
    """All 4 IEEE grids load correctly with the correct dimensions."""
    from core.digital_twin.multi_grid_topology import MultiGridTopology, SUPPORTED_GRIDS

    expected = {
        "ieee14":  {"buses": 14, "min_lines": 15},
        "ieee39":  {"buses": 39, "min_lines": 40},
        "ieee57":  {"buses": 57, "min_lines": 70},
        "ieee118": {"buses": 118, "min_lines": 150},
    }

    for g in SUPPORTED_GRIDS:
        topo = MultiGridTopology(g)
        summary = topo.get_summary()

        assert summary["num_buses"] == expected[g]["buses"], \
            f"{g}: expected {expected[g]['buses']} buses, got {summary['num_buses']}"
        assert summary["num_lines"] >= expected[g]["min_lines"], \
            f"{g}: expected >= {expected[g]['min_lines']} lines, got {summary['num_lines']}"
        assert len(topo.generators) > 0, f"{g}: no generators found"
        assert len(topo.loads) > 0, f"{g}: no loads found"
        assert len(topo.lines) == summary["num_lines"], \
            f"{g}: line count mismatch"
        assert topo.slack_bus >= 0, f"{g}: invalid slack bus"

    print("✓ test_multi_grid_topology PASSED")


# -----------------------------------------------------------------------
# Test 2: Unified Grid Encoder — output shape is always (128,)
# -----------------------------------------------------------------------
def test_unified_grid_encoder():
    """Encoder outputs z ∈ R^128 for all 4 grid sizes."""
    from core.digital_twin.multi_grid_topology import MultiGridTopology, SUPPORTED_GRIDS
    from core.transfer.unified_grid_encoder import UnifiedGridEncoder

    encoder = UnifiedGridEncoder()

    for g in SUPPORTED_GRIDS:
        topo = MultiGridTopology(g)
        z = encoder.encode(topo)

        assert isinstance(z, np.ndarray), f"{g}: encoder output is not ndarray"
        assert z.shape == (128,), \
            f"{g}: expected shape (128,), got {z.shape}"
        assert not np.any(np.isnan(z)), f"{g}: NaN values in latent vector"
        assert not np.any(np.isinf(z)), f"{g}: Inf values in latent vector"
        # L2-normalized
        norm = np.linalg.norm(z)
        assert norm > 0.0, f"{g}: zero latent vector"

    # Ensure different grids produce different embeddings
    topos = [MultiGridTopology(g) for g in SUPPORTED_GRIDS]
    zs = [encoder.encode(t) for t in topos]
    # At least one pair should be distinguishable
    diffs = [np.linalg.norm(zs[i] - zs[j])
             for i in range(len(zs)) for j in range(i+1, len(zs))]
    assert any(d > 1e-6 for d in diffs), \
        "All grid embeddings are identical (encoder is not discriminative)"

    print("✓ test_unified_grid_encoder PASSED")


# -----------------------------------------------------------------------
# Test 3: Domain Adapter — MMD and CORAL are non-negative scalars
# -----------------------------------------------------------------------
def test_domain_adapter():
    """MMD and CORAL losses are non-negative scalars for any input pair."""
    from core.transfer.domain_adapter import DomainAdapter

    adapter = DomainAdapter()

    np.random.seed(42)
    # Case 1: identical distributions → MMD ≈ 0
    z_same = np.random.randn(20, 128)
    mmd_same = adapter.mmd_loss(z_same, z_same)
    assert mmd_same >= 0.0, f"MMD of identical distributions is negative: {mmd_same}"
    assert mmd_same < 0.1, f"MMD of identical distributions is too large: {mmd_same}"

    # Case 2: shifted distributions → MMD > 0
    z_s = np.random.randn(10, 128)
    z_t = np.random.randn(8, 128) + 5.0  # large shift
    mmd_shifted = adapter.mmd_loss(z_s, z_t)
    assert mmd_shifted >= 0.0, f"MMD is negative: {mmd_shifted}"
    assert mmd_shifted > mmd_same, \
        f"MMD of shifted distributions ({mmd_shifted}) not > identical ({mmd_same})"

    # CORAL
    coral_val = adapter.coral_loss(z_s, z_t)
    assert coral_val >= 0.0, f"CORAL loss is negative: {coral_val}"

    # Single-vector case (edge case)
    z_single = np.random.randn(1, 128)
    mmd_single = adapter.mmd_loss(z_single, z_single)
    assert mmd_single >= 0.0

    # Alignment matrix
    embeddings = {
        "ieee14":  np.random.randn(5, 128),
        "ieee39":  np.random.randn(5, 128) + 0.5,
    }
    matrix, labels = adapter.alignment_matrix(embeddings, method="mmd")
    assert matrix.shape == (2, 2), f"Alignment matrix shape is wrong: {matrix.shape}"
    assert matrix[0, 0] == 0.0, "Self-alignment should be 0"
    assert matrix[0, 1] >= 0.0, "Cross-alignment should be non-negative"

    print("✓ test_domain_adapter PASSED")


# -----------------------------------------------------------------------
# Test 4: Transfer Pathogen Agent — zero-shot attack returns valid output
# -----------------------------------------------------------------------
def test_transfer_pathogen_agent():
    """Zero-shot attack returns valid line targets and non-negative load shed."""
    from core.digital_twin.multi_grid_topology import MultiGridTopology
    from core.adversarial.transfer_pathogen_agent import TransferPatogenAgent

    np.random.seed(42)

    # Train minimally on IEEE39
    agent = TransferPatogenAgent(num_targets=3, seed=42)
    topo39 = MultiGridTopology("ieee39")
    rewards = agent.train(topo39, episodes=5, k=3, verbose=False, grid_label="test")

    assert len(rewards) == 5, "Expected 5 episode rewards"
    assert all(isinstance(r, float) for r in rewards), "Rewards should be floats"

    # Zero-shot on IEEE57
    topo57 = MultiGridTopology("ieee57")
    result = agent.zero_shot_attack(topo57, k=3)

    assert "load_shed" in result, "Missing load_shed in result"
    assert "cascade_size" in result, "Missing cascade_size in result"
    assert "blackout" in result, "Missing blackout in result"
    assert result["load_shed"] >= 0.0, "Load shed cannot be negative"
    assert result["cascade_size"] >= 0, "Cascade size cannot be negative"
    assert result["blackout"] in [0.0, 1.0], "Blackout must be 0 or 1"
    assert len(result["tripped_lines"]) > 0, "No lines were tripped"
    assert len(result["tripped_lines"]) <= 3, "More than K lines tripped"

    # Check that tripped lines are valid line IDs for ieee57
    valid_ids = set(l["id"] for l in topo57.lines)
    for lid in result["tripped_lines"]:
        assert lid in valid_ids, f"Invalid line ID: {lid}"

    print("✓ test_transfer_pathogen_agent PASSED")


# -----------------------------------------------------------------------
# Test 5: Multi-Grid Environment — curriculum and grid switching
# -----------------------------------------------------------------------
def test_multigrid_env():
    """MultiGridEnv correctly loads all grids and switches by curriculum stage."""
    from core.adversarial.multigrid_env import MultiGridEnv, CURRICULUM_STAGES

    env = MultiGridEnv(curriculum_stage=1, seed=42)

    # Stage 1: only ieee14
    active = env._active_grids()
    assert "ieee14" in active, f"Stage 1 should contain ieee14, got {active}"
    assert len(active) == 1, f"Stage 1 should have 1 grid, got {active}"

    topo = env.reset(curriculum_stage=1)
    assert topo.grid_name == "ieee14", f"Stage 1 should return ieee14, got {topo.grid_name}"

    # Advance to stage 2
    new_stage = env.advance_curriculum()
    assert new_stage == 2, f"Expected stage 2, got {new_stage}"
    active2 = env._active_grids()
    assert "ieee39" in active2, f"Stage 2 should contain ieee39"
    assert len(active2) == 2, f"Stage 2 should have 2 grids"

    # Stage 4: all grids
    env2 = MultiGridEnv(curriculum_stage=4, seed=42)
    active4 = env2._active_grids()
    assert len(active4) == 4, f"Stage 4 should have 4 grids, got {active4}"

    # Test reset with explicit grid
    topo57 = env2.reset(grid_name="ieee57")
    assert topo57.grid_name == "ieee57"

    # Test step
    import numpy as np
    targets = np.array([0, 1, 2])
    metrics = env2.step(targets, k=3)
    assert "load_shed" in metrics
    assert "reward" in metrics
    assert metrics["load_shed"] >= 0.0

    print("✓ test_multigrid_env PASSED")


# -----------------------------------------------------------------------
# Test 6: Zero-Padded Attack Representation
# -----------------------------------------------------------------------
def test_zero_padded_attack():
    """Policy outputs 186-dim logits; valid actions for smaller grids are masked."""
    from core.adversarial.transfer_pathogen_agent import (
        PolicyNetwork, MAX_ACTION_DIM, TransferPatogenAgent
    )
    from core.digital_twin.multi_grid_topology import MultiGridTopology

    np.random.seed(42)
    policy = PolicyNetwork(latent_dim=128, action_dim=MAX_ACTION_DIM, seed=42)

    z = np.random.randn(128).astype(np.float32)

    for grid_name, expected_lines in [
        ("ieee14", 20),
        ("ieee39", 46),
        ("ieee57", 80),
        ("ieee118", 186),
    ]:
        topo = MultiGridTopology(grid_name)
        n_valid = len(topo.lines)

        targets, log_prob = policy.sample_action(z, n_valid, k=3)

        # Targets must be within valid range
        assert len(targets) <= 3, f"{grid_name}: more than 3 targets"
        assert all(0 <= t < n_valid for t in targets), \
            f"{grid_name}: target indices out of valid range [0, {n_valid})"
        assert np.isfinite(log_prob), f"{grid_name}: log_prob is not finite: {log_prob}"

    # Full-size check: for ieee118, all 186 actions should be valid
    topo118 = MultiGridTopology("ieee118")
    n_valid_118 = len(topo118.lines)
    targets118, _ = policy.sample_action(z, n_valid_118, k=5)
    assert all(0 <= t < n_valid_118 for t in targets118), \
        "IEEE118 targets out of range"

    print("✓ test_zero_padded_attack PASSED")
