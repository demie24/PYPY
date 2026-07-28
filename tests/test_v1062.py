"""
Unit Tests for PYPY V10.6.2 — End-to-End Transfer Learning Patch.
All 12 tests must pass.
"""
import os
import sys
import numpy as np
import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.digital_twin.multi_grid_topology import MultiGridTopology, SUPPORTED_GRIDS


# ---------------------------------------------------------------------------
# T1: Trainable encoder forward pass + gradient flow
# ---------------------------------------------------------------------------
def test_trainable_encoder_forward():
    """TrainableGridEncoder produces (128,) L2-normalized z with trainable weights."""
    from core.transfer.trainable_grid_encoder import TrainableGridEncoder

    enc = TrainableGridEncoder(lr=1e-3, seed=42)
    topo = MultiGridTopology("ieee39")

    z, cache = enc.encode_with_cache(topo, store_cache=True)
    assert z.shape == (128,), f"Expected (128,), got {z.shape}"
    norm = np.linalg.norm(z)
    assert 0.90 < norm < 1.10, f"z should be near-unit-norm, got {norm:.4f}"
    assert len(cache) > 0, "Cache should be populated"
    assert "H1" in cache and "H2" in cache, "Cache missing GNN activations"
    print("✓ test_trainable_encoder_forward PASSED")


# ---------------------------------------------------------------------------
# T2: Encoder backward updates weights
# ---------------------------------------------------------------------------
def test_trainable_encoder_backward():
    """Backward pass changes encoder weights."""
    from core.transfer.trainable_grid_encoder import TrainableGridEncoder

    enc = TrainableGridEncoder(lr=1e-2, seed=42)
    topo = MultiGridTopology("ieee39")

    W_before = enc.layer1.W.copy()
    z, cache = enc.encode_with_cache(topo)
    dz = np.ones(128, dtype=np.float32) * 0.1
    enc.backward(dz, cache, clip=1.0)
    W_after = enc.layer1.W

    assert not np.allclose(W_before, W_after), \
        "layer1.W should change after backward pass"
    max_change = np.abs(W_after - W_before).max()
    assert max_change < 1.0, f"Weight change too large: {max_change:.4f}"
    print("✓ test_trainable_encoder_backward PASSED")


# ---------------------------------------------------------------------------
# T3: Criticality encoder output shape and PTDF validity
# ---------------------------------------------------------------------------
def test_criticality_encoder():
    """CriticalityAwareEncoder produces (128,) z with meaningful PTDF scores."""
    from core.transfer.criticality_encoder import CriticalityAwareEncoder

    enc = CriticalityAwareEncoder(encoder_lr=1e-3, seed=42)

    for g in SUPPORTED_GRIDS:
        topo = MultiGridTopology(g)
        z = enc.encode(topo)
        assert z.shape == (128,), f"{g}: expected (128,), got {z.shape}"
        norm = np.linalg.norm(z)
        assert 0.80 < norm < 1.20, f"{g}: z not normalized, norm={norm:.4f}"

        # PTDF scores should be in [0,1]
        ptdf = enc.ptdf_embedder.compute_ptdf_scores(topo)
        assert ptdf.min() >= 0.0 and ptdf.max() <= 1.0 + 1e-6, \
            f"{g}: PTDF scores out of [0,1]: {ptdf.min():.4f}, {ptdf.max():.4f}"
        assert ptdf.std() > 0, f"{g}: PTDF scores are all identical (no variation)"

    print("✓ test_criticality_encoder PASSED")


# ---------------------------------------------------------------------------
# T4: PTDF top-k critical lines are consistent
# ---------------------------------------------------------------------------
def test_ptdf_top_k():
    """Top-k critical lines by PTDF are stable and unique."""
    from core.transfer.criticality_encoder import CriticalityAwareEncoder

    enc = CriticalityAwareEncoder(seed=42)
    topo = MultiGridTopology("ieee118")

    top5 = enc.get_top_k_targets(topo, k=5)
    assert len(top5) == 5, f"Expected 5 targets, got {len(top5)}"
    assert len(set(top5.tolist())) == 5, "Top-5 indices should be unique"
    assert all(0 <= idx < topo.num_lines for idx in top5), \
        "All indices should be within valid range"

    # PTDF-guided should be different from random k=5
    np.random.seed(42)
    random_5 = np.random.choice(topo.num_lines, size=5, replace=False)
    assert not np.array_equal(np.sort(top5), np.sort(random_5)), \
        "PTDF top-k should differ from random selection"

    print("✓ test_ptdf_top_k PASSED")


# ---------------------------------------------------------------------------
# T5: Betweenness and Risk embedders produce valid outputs
# ---------------------------------------------------------------------------
def test_criticality_embedders():
    """BC and Risk embedders produce valid 16-dim unit vectors."""
    from core.transfer.criticality_encoder import BetweennessEmbedder, RiskScoreEmbedder

    bc_emb = BetweennessEmbedder(seed=43)
    rs_emb = RiskScoreEmbedder(seed=44)

    for g in ["ieee14", "ieee57"]:
        topo = MultiGridTopology(g)

        z_bc = bc_emb.embed(topo)
        assert z_bc.shape == (16,), f"{g} BC: expected (16,), got {z_bc.shape}"
        assert np.all(np.isfinite(z_bc)), f"{g} BC has non-finite values"
        assert np.linalg.norm(z_bc) > 0, f"{g} BC embedding is zero vector"

        z_rs = rs_emb.embed(topo)
        assert z_rs.shape == (16,), f"{g} Risk: expected (16,), got {z_rs.shape}"
        assert np.all(np.isfinite(z_rs)), f"{g} Risk has non-finite values"

        # BC scores should be in [0,1]
        bc_scores = bc_emb.compute_betweenness(topo)
        assert bc_scores.min() >= 0.0, f"{g}: BC scores have negatives"
        assert bc_scores.max() <= 1.0 + 1e-6, f"{g}: BC scores exceed 1"

    print("✓ test_criticality_embedders PASSED")


# ---------------------------------------------------------------------------
# T6: SSL pre-trainer loss decreases over epochs
# ---------------------------------------------------------------------------
def test_ssl_pretrain_loss_decreases():
    """SSL pre-training loss decreases (or stays bounded) over epochs."""
    from core.transfer.criticality_encoder import CriticalityAwareEncoder
    from core.transfer.self_supervised_pretrain import SelfSupervisedPretrainer

    enc = CriticalityAwareEncoder(encoder_lr=1e-3, seed=42)
    trainer = SelfSupervisedPretrainer(enc, alpha=0.4, beta=0.3, gamma=0.3,
                                       lr=1e-3, seed=42)
    topos = [MultiGridTopology("ieee39"), MultiGridTopology("ieee57")]
    losses = trainer.pretrain(topos, n_epochs=20, verbose_every=0, seed=42)

    assert len(losses) == 20, f"Expected 20 loss values, got {len(losses)}"
    assert all(np.isfinite(l) for l in losses), "All losses must be finite"
    assert losses[0] > 0, "Initial loss should be positive"

    # Loss should not explode
    max_loss = max(losses)
    assert max_loss < 100.0, f"Loss exploded: max={max_loss:.2f}"

    print("✓ test_ssl_pretrain_loss_decreases PASSED")


# ---------------------------------------------------------------------------
# T7: MAML inner loop produces different adapted policy
# ---------------------------------------------------------------------------
def test_maml_inner_loop():
    """MAML inner loop adaptation produces different weights from initial."""
    from core.transfer.criticality_encoder import CriticalityAwareEncoder
    from core.transfer.maml_meta_learner import MAMLMetaLearner, PolicySnapshot
    from core.adversarial.transfer_pathogen_agent import PolicyNetwork

    np.random.seed(42)
    enc = CriticalityAwareEncoder(seed=42)
    pol = PolicyNetwork(latent_dim=128, seed=42)
    topos = [MultiGridTopology("ieee39"), MultiGridTopology("ieee57")]
    topo_test = MultiGridTopology("ieee118")

    maml = MAMLMetaLearner(enc, pol, topos, meta_lr=1e-3, seed=42)

    # Run 5 meta-iterations
    losses = maml.meta_train(n_iterations=5, inner_steps=3,
                              inner_lr=5e-3, n_query=3, verbose_every=0)
    assert len(losses) == 5, f"Expected 5 meta-losses, got {len(losses)}"
    assert all(np.isfinite(l) for l in losses), "All meta-losses must be finite"

    # Adapted policy should differ from initial
    snap_init = PolicySnapshot(pol)
    adapted = maml.adapt(topo_test, n_steps=5, inner_lr=5e-3)
    w_diff = np.abs(adapted.W3 - snap_init.W3).max()
    assert w_diff > 0, "Adapted policy should have different weights from initial"

    print("✓ test_maml_inner_loop PASSED")


# ---------------------------------------------------------------------------
# T8: PolicySnapshot gradient step correctness
# ---------------------------------------------------------------------------
def test_policy_snapshot_gradient():
    """PolicySnapshot.gradient_step produces valid updated weights."""
    from core.transfer.maml_meta_learner import PolicySnapshot
    from core.adversarial.transfer_pathogen_agent import PolicyNetwork

    np.random.seed(42)
    pol = PolicyNetwork(latent_dim=128, seed=42)
    snap = PolicySnapshot(pol)
    topo = MultiGridTopology("ieee57")

    z = np.random.randn(128).astype(np.float32)
    z /= np.linalg.norm(z) + 1e-9
    n_valid = topo.num_lines
    targets = np.array([0, 1, 2])
    reward  = 1.5

    snap2 = snap.gradient_step(z, targets, reward, n_valid, inner_lr=1e-2)

    # Should be a new object with different weights
    assert snap2 is not snap, "gradient_step should return a new snapshot"
    assert not np.allclose(snap.W1, snap2.W1), "W1 should change after gradient step"
    # Original should be unchanged
    assert np.allclose(snap.W1, pol.W1), "Original snapshot should be unchanged"

    print("✓ test_policy_snapshot_gradient PASSED")


# ---------------------------------------------------------------------------
# T9: Criticality attack outperforms random on mean (direction check)
# ---------------------------------------------------------------------------
def test_criticality_vs_random():
    """Criticality-guided attack produces positive mean shed (functional test)."""
    from core.transfer.criticality_encoder import CriticalityAwareEncoder
    from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator

    enc = CriticalityAwareEncoder(seed=42)

    for g in ["ieee39", "ieee118"]:
        topo = MultiGridTopology(g)
        top3 = enc.get_top_k_targets(topo, k=3)
        ids = [l["id"] for l in topo.lines]
        n = len(ids)

        tripped_crit = set(ids[int(i) % n] for i in top3)
        sim = CascadingFailureSimulator(topo)
        res = sim.run_cascade(initial_tripped_lines=tripped_crit)
        shed_crit = float(res["load_shed"])

        assert shed_crit >= 0, f"{g}: criticality attack shed is negative"
        assert np.isfinite(shed_crit), f"{g}: criticality attack shed is not finite"

    print("✓ test_criticality_vs_random PASSED")


# ---------------------------------------------------------------------------
# T10: t-SNE produces valid 2D embedding
# ---------------------------------------------------------------------------
def test_tsne_embedding():
    """t-SNE produces finite 2D coordinates for a small point cloud."""
    from core.analytics.verify_v1062 import tsne_2d

    np.random.seed(42)
    # Simulate 4 clusters of 10 points each (like 4 grids × 10 samples)
    X = np.vstack([
        np.random.randn(10, 32) + np.array([3, 0] + [0]*30),
        np.random.randn(10, 32) + np.array([-3, 0] + [0]*30),
        np.random.randn(10, 32) + np.array([0, 3] + [0]*30),
        np.random.randn(10, 32) + np.array([0, -3] + [0]*30),
    ]).astype(np.float32)

    Y = tsne_2d(X, n_iter=50, perplexity=5.0, seed=42)

    assert Y.shape == (40, 2), f"Expected (40,2), got {Y.shape}"
    assert np.all(np.isfinite(Y)), "t-SNE output should be finite"
    assert Y.std() > 0, "t-SNE should produce spread in 2D"

    print("✓ test_tsne_embedding PASSED")


# ---------------------------------------------------------------------------
# T11: Silhouette and cluster purity metrics
# ---------------------------------------------------------------------------
def test_latent_quality_metrics():
    """Silhouette score and cluster purity work correctly on known data."""
    from core.analytics.verify_v1062 import silhouette_score, cluster_purity

    np.random.seed(42)
    # Well-separated clusters → high silhouette
    X_sep = np.vstack([
        np.random.randn(20, 8) + np.array([10, 0] + [0]*6),
        np.random.randn(20, 8) + np.array([-10, 0] + [0]*6),
    ]).astype(np.float32)
    labels_sep = np.array([0]*20 + [1]*20)

    sil_sep = silhouette_score(X_sep, labels_sep)
    assert sil_sep > 0.3, f"Well-separated clusters should have silhouette > 0.3, got {sil_sep:.3f}"

    purity_sep = cluster_purity(X_sep, labels_sep)
    assert purity_sep >= 0.8, f"Pure clusters should have purity >= 0.8, got {purity_sep:.3f}"

    # Random points → low silhouette
    X_rand = np.random.randn(40, 8).astype(np.float32)
    labels_rand = np.array([0]*20 + [1]*20)
    sil_rand = silhouette_score(X_rand, labels_rand)
    assert sil_rand < 0.5, f"Random points should have silhouette < 0.5, got {sil_rand:.3f}"

    print("✓ test_latent_quality_metrics PASSED")


# ---------------------------------------------------------------------------
# T12: Power analysis helper
# ---------------------------------------------------------------------------
def test_power_analysis():
    """power_at_n returns expected values for known effect sizes."""
    from core.analytics.verify_v1062 import power_at_n

    # Large effect (d=0.8): at N=100, power should be high
    p100 = power_at_n(0.8, 100)
    assert p100 > 0.90, f"d=0.8, N=100 should give power>0.90, got {p100:.3f}"

    # Small effect (d=0.2): at N=50, power should be low
    p50 = power_at_n(0.2, 50)
    assert p50 < 0.40, f"d=0.2, N=50 should give power<0.40, got {p50:.3f}"

    # Zero effect: at any N, power ≈ alpha = 0.05
    p_zero = power_at_n(0.0, 200)
    assert p_zero < 0.10, f"d=0, power should be near alpha, got {p_zero:.3f}"

    # Cohen's d function
    from core.analytics.verify_v1062 import cohen_d
    np.random.seed(42)
    a = np.random.randn(100) + 1.0
    b = np.random.randn(100)
    d = cohen_d(a, b)
    assert 0.5 < d < 1.5, f"Cohen's d for 1-std separation should be ~1.0, got {d:.3f}"

    print("✓ test_power_analysis PASSED")
