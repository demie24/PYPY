"""
Unified Grid Encoder — PYPY V10.6 Cross-Grid Transfer Learning.

Produces a topology-invariant fixed-dimensional latent vector z ∈ R^128
from any IEEE grid (14, 39, 57, or 118 buses) using a pure-numpy
GraphSAGE-style message-passing architecture with global pooling.

Architecture:
    Layer 1: NodeFeatures(6) + AggNeighborFeatures(6) → FC(12→64) → ReLU
    Layer 2: NodeFeatures(64) + AggNeighborFeatures(64) → FC(128→64) → ReLU
    Global Pooling: Mean + Max of all node embeddings → FC(128→128) → z

All weights are fixed (no gradient training needed in this numpy implementation).
The encoder acts as a deterministic feature extractor producing a canonical
latent embedding of any grid topology.
"""
import os
import sys
import numpy as np
from typing import Dict, Any, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


class GraphSAGELayer:
    """
    Single GraphSAGE-style message passing layer (numpy, fixed weights).
    Aggregates neighbor features and concatenates with self features.
    Weight matrix W is initialized deterministically (seeded).
    """

    def __init__(self, in_dim: int, out_dim: int, seed: int = 42):
        rng = np.random.RandomState(seed)
        # Weights for [self_feat || neighbor_agg] → out_dim
        self.W = rng.randn(in_dim * 2, out_dim) * np.sqrt(2.0 / (in_dim * 2))
        self.b = np.zeros(out_dim)

    def forward(self, H: np.ndarray, adj: np.ndarray) -> np.ndarray:
        """
        Args:
            H: Node feature matrix (N, in_dim)
            adj: Normalized adjacency matrix (N, N)
        Returns:
            H_new: Updated node features (N, out_dim)
        """
        # Aggregate: mean of neighbor features
        neighbor_agg = adj @ H  # (N, in_dim)
        # Concatenate self + aggregated
        combined = np.concatenate([H, neighbor_agg], axis=1)  # (N, 2*in_dim)
        # Linear transform + ReLU
        H_new = combined @ self.W + self.b
        return np.maximum(H_new, 0)  # ReLU


class UnifiedGridEncoder:
    """
    Topology-invariant grid encoder based on GraphSAGE message passing.

    Encodes any IEEE grid topology into a fixed-size z ∈ R^128 vector.

    Usage:
        encoder = UnifiedGridEncoder()
        z = encoder.encode(topo)  # z.shape == (128,)
    """

    LATENT_DIM = 128

    def __init__(self):
        # Layer 1: node_feat(6) + neighbor_agg(6) → 64
        self.layer1 = GraphSAGELayer(in_dim=6, out_dim=64, seed=42)
        # Layer 2: node_feat(64) + neighbor_agg(64) → 64
        self.layer2 = GraphSAGELayer(in_dim=64, out_dim=64, seed=43)
        # Final projection: mean_pool(64) + max_pool(64) → 128
        rng = np.random.RandomState(44)
        self.W_proj = rng.randn(128, 128) * np.sqrt(2.0 / 128)
        self.b_proj = np.zeros(128)

    def _build_node_features(self, topo) -> np.ndarray:
        """
        Builds a 6-dimensional feature vector for each bus:
            [is_generator, is_load, is_slack, P_nom, degree_norm, bus_idx_norm]
        """
        N = topo.num_buses
        features = np.zeros((N, 6), dtype=np.float32)

        max_p = max(
            [g["P_nom"] for g in topo.generators.values()] +
            [l["P_nom"] for l in topo.loads.values()] + [1.0]
        )

        # Count degree
        degrees = np.zeros(N)
        for line in topo.lines:
            f, t = line["from"], line["to"]
            if 0 <= f < N:
                degrees[f] += 1
            if 0 <= t < N:
                degrees[t] += 1
        max_deg = max(degrees.max(), 1.0)

        for i in range(N):
            features[i, 0] = 1.0 if i in topo.generators else 0.0
            features[i, 1] = 1.0 if i in topo.loads else 0.0
            features[i, 2] = 1.0 if i == topo.slack_bus else 0.0
            features[i, 3] = topo.generators[i]["P_nom"] / max_p if i in topo.generators else (
                -topo.loads[i]["P_nom"] / max_p if i in topo.loads else 0.0
            )
            features[i, 4] = degrees[i] / max_deg
            features[i, 5] = float(i) / max(N - 1, 1)

        return features

    def _build_adj_matrix(self, topo) -> np.ndarray:
        """
        Builds a row-normalized adjacency matrix (with self-loops) of shape (N, N).
        """
        N = topo.num_buses
        A = np.eye(N, dtype=np.float32)  # self-loops

        for line in topo.lines:
            f, t = line["from"], line["to"]
            if 0 <= f < N and 0 <= t < N:
                A[f, t] = 1.0
                A[t, f] = 1.0

        # Row-normalize
        row_sums = A.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums < 1e-9, 1.0, row_sums)
        return A / row_sums

    def encode(self, topo) -> np.ndarray:
        """
        Encodes a grid topology into a fixed 128-dim latent vector.

        Args:
            topo: Any object with .num_buses, .generators, .loads, .lines, .slack_bus
        Returns:
            z: np.ndarray of shape (128,)
        """
        H0 = self._build_node_features(topo)   # (N, 6)
        adj = self._build_adj_matrix(topo)      # (N, N)

        # Two rounds of message passing
        H1 = self.layer1.forward(H0, adj)       # (N, 64)
        H2 = self.layer2.forward(H1, adj)       # (N, 64)

        # Global pooling: mean + max → (128,)
        mean_pool = H2.mean(axis=0)             # (64,)
        max_pool  = H2.max(axis=0)              # (64,)
        pooled = np.concatenate([mean_pool, max_pool])  # (128,)

        # Final projection + ReLU → z ∈ R^128
        z = pooled @ self.W_proj + self.b_proj
        z = np.maximum(z, 0)

        # L2-normalize for stable downstream distance computations
        norm = np.linalg.norm(z) + 1e-9
        return (z / norm).astype(np.float32)

    def encode_batch(self, topos: list) -> np.ndarray:
        """
        Encodes a list of grids into a matrix of shape (len(topos), 128).
        """
        return np.stack([self.encode(t) for t in topos], axis=0)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(project_root))
    from core.digital_twin.multi_grid_topology import MultiGridTopology

    encoder = UnifiedGridEncoder()
    for gname in ["ieee14", "ieee39", "ieee57", "ieee118"]:
        topo = MultiGridTopology(gname)
        z = encoder.encode(topo)
        print(f"{gname}: z.shape={z.shape}, norm={np.linalg.norm(z):.4f}, "
              f"mean={z.mean():.4f}, std={z.std():.4f}")
