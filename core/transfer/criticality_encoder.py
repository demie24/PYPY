"""
Criticality-Aware Latent Space — PYPY V10.6.2.

Augments the GraphSAGE latent vector with physics-based criticality features:

  z_final = LayerNorm(concat(
      z_gnn   (64-dim)  ← trainable GraphSAGE output
      z_ptdf  (32-dim)  ← PTDF sensitivity scores embedding
      z_bc    (16-dim)  ← Extended Betweenness Centrality embedding
      z_risk  (16-dim)  ← Load/Capacity Risk score embedding
  )) → 128-dim

Key insight: PTDF scores directly measure how much each line's outage affects
power flows in the rest of the network. Explicitly encoding these allows the
policy to learn "attack PTDF-critical lines" → larger cascades → p<0.05 vs random.

All computations are pure numpy. No external dependencies.
"""
import os
import sys
import numpy as np
from typing import Dict, List, Tuple, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


# ---------------------------------------------------------------------------
# PTDF Embedder
# ---------------------------------------------------------------------------
class PTDFEmbedder:
    """
    Computes a 32-dimensional embedding from PTDF sensitivity scores.

    PTDF (Power Transfer Distribution Factor) measures how a line outage
    redistributes power flows. High PTDF → more critical line.

    For each line l:
        ptdf_score[l] = sum_{l'≠l} |ΔF_l'| / (line_capacity_l + 1e-9)
    Approximated using DC power flow sensitivity (B-matrix based).
    """

    OUT_DIM = 32

    def __init__(self, seed: int = 42):
        rng = np.random.RandomState(seed)
        # Projection: (n_lines,) → (32,) via learnable projection
        # The input is normalized PTDF scores, projected to fixed 32-dim
        # We use a fixed random projection (Gaussian) as feature hash
        # The trainable part is in the main encoder backward
        self._proj = rng.randn(256, self.OUT_DIM).astype(np.float32) * np.sqrt(2.0 / 256)

    def compute_ptdf_scores(self, topo) -> np.ndarray:
        """
        Computes approximate PTDF sensitivity score for each line.

        Uses B-matrix approximation:
          1. Build susceptance matrix B from line reactances X
          2. PTDF[k,l] = (B^-1 row differences) — approximated here
          3. Return per-line aggregate sensitivity score

        Returns: (num_lines,) array of PTDF scores, normalized to [0,1]
        """
        N = topo.num_buses
        L = len(topo.lines)
        if L == 0:
            return np.zeros(1)

        # Build susceptance matrix B
        B = np.zeros((N, N), dtype=np.float64)
        for line in topo.lines:
            f, t = line["from"], line["to"]
            if 0 <= f < N and 0 <= t < N and f != t:
                b_kl = 1.0 / (line["X"] + 1e-9)
                B[f, f] += b_kl
                B[t, t] += b_kl
                B[f, t] -= b_kl
                B[t, f] -= b_kl

        # Reduced B (remove slack bus row/col for invertibility)
        slack = topo.slack_bus if hasattr(topo, 'slack_bus') else 0
        non_slack = [i for i in range(N) if i != slack]
        if len(non_slack) < 2:
            return np.ones(L) / L

        B_red = B[np.ix_(non_slack, non_slack)]

        # Pseudo-inverse for stability
        try:
            B_inv = np.linalg.pinv(B_red)
        except np.linalg.LinAlgError:
            return np.ones(L) / L

        # For each line, compute PTDF = b_kl * (B_inv[f] - B_inv[t])
        ptdf_scores = np.zeros(L, dtype=np.float32)
        non_slack_set = set(non_slack)
        ns_idx = {bus: i for i, bus in enumerate(non_slack)}

        for li, line in enumerate(topo.lines):
            f, t = line["from"], line["to"]
            b_kl = 1.0 / (line["X"] + 1e-9)
            # Aggregate PTDF impact: sum of |PTDF[k,l]| over all non-slack buses
            impact = 0.0
            if f in ns_idx and t in ns_idx:
                row_diff = B_inv[ns_idx[f], :] - B_inv[ns_idx[t], :]
                impact = b_kl * np.sum(np.abs(row_diff))
            elif f in ns_idx:
                impact = b_kl * np.sum(np.abs(B_inv[ns_idx[f], :]))
            elif t in ns_idx:
                impact = b_kl * np.sum(np.abs(B_inv[ns_idx[t], :]))
            ptdf_scores[li] = float(impact)

        # Normalize to [0, 1]
        max_s = ptdf_scores.max() + 1e-9
        return ptdf_scores / max_s

    def embed(self, topo) -> np.ndarray:
        """
        Returns a 32-dimensional PTDF embedding for the topology.

        Strategy: hash the (sorted, normalized) PTDF score vector into
        a fixed 32-dim space via:
          1. Sort scores descending (order-invariant summary)
          2. Take top-256 (zero-pad if fewer lines)
          3. Apply fixed Gaussian projection → 32-dim → ReLU → normalize
        """
        scores = self.compute_ptdf_scores(topo)

        # Create a 256-dim sorted summary (zero-padded)
        sorted_s = np.sort(scores)[::-1]
        summary = np.zeros(256, dtype=np.float32)
        n = min(len(sorted_s), 256)
        summary[:n] = sorted_s[:n]

        # Additional statistics in last few dims
        summary[248] = scores.mean() if len(scores) > 0 else 0.0
        summary[249] = scores.std()  if len(scores) > 0 else 0.0
        summary[250] = scores.max()  if len(scores) > 0 else 0.0
        summary[251] = float(len(scores)) / 256.0

        # Project to 32-dim
        z = summary @ self._proj           # (32,)
        z = np.maximum(z, 0.0)            # ReLU
        norm = np.linalg.norm(z) + 1e-9
        return (z / norm).astype(np.float32)

    def top_k_critical_lines(self, topo, k: int = 10) -> np.ndarray:
        """Returns indices of the top-k PTDF-critical lines."""
        scores = self.compute_ptdf_scores(topo)
        k = min(k, len(scores))
        return np.argsort(scores)[::-1][:k].astype(np.int32)


# ---------------------------------------------------------------------------
# Betweenness Centrality Embedder
# ---------------------------------------------------------------------------
class BetweennessEmbedder:
    """
    Computes a 16-dimensional embedding from extended betweenness centrality.

    Line betweenness centrality: fraction of shortest paths passing through edge.
    High betweenness → topological bottleneck → critical for grid connectivity.
    """

    OUT_DIM = 16

    def __init__(self, seed: int = 43):
        rng = np.random.RandomState(seed)
        self._proj = rng.randn(64, self.OUT_DIM).astype(np.float32) * np.sqrt(2.0 / 64)

    def compute_betweenness(self, topo) -> np.ndarray:
        """
        Approximate edge betweenness centrality (BFS-based).
        Uses Brandes algorithm approximation for speed.
        Returns (num_lines,) normalized betweenness scores.
        """
        N = topo.num_buses
        L = len(topo.lines)
        if N == 0 or L == 0:
            return np.zeros(L)

        # Build adjacency as edge index mapping: (f,t) → line index
        adj: Dict[int, List[int]] = {i: [] for i in range(N)}
        edge_to_line: Dict[Tuple[int,int], int] = {}
        for li, line in enumerate(topo.lines):
            f, t = line["from"], line["to"]
            if 0 <= f < N and 0 <= t < N and f != t:
                adj[f].append(t)
                adj[t].append(f)
                edge_to_line[(min(f,t), max(f,t))] = li

        line_bc = np.zeros(L, dtype=np.float64)

        # BFS from each source node (sample up to 30 for large grids)
        sources = list(range(N))
        if N > 30:
            rng_local = np.random.RandomState(42)
            sources = rng_local.choice(N, size=30, replace=False).tolist()

        for s in sources:
            # BFS
            stack = []
            pred: Dict[int, List[int]] = {w: [] for w in range(N)}
            sigma = np.zeros(N); sigma[s] = 1.0
            dist = np.full(N, -1); dist[s] = 0
            queue = [s]
            qi = 0
            while qi < len(queue):
                v = queue[qi]; qi += 1
                stack.append(v)
                for w in adj[v]:
                    if dist[w] < 0:
                        queue.append(w)
                        dist[w] = dist[v] + 1
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        pred[w].append(v)

            # Accumulation
            delta = np.zeros(N)
            while stack:
                w = stack.pop()
                for v in pred[w]:
                    c = (sigma[v] / (sigma[w] + 1e-9)) * (1.0 + delta[w])
                    delta[v] += c
                    # Add to edge betweenness
                    key = (min(v, w), max(v, w))
                    if key in edge_to_line:
                        line_bc[edge_to_line[key]] += c

        # Normalize
        scale = (N - 1) * (N - 2)
        if scale > 0:
            line_bc /= scale
        max_bc = line_bc.max() + 1e-9
        return (line_bc / max_bc).astype(np.float32)

    def embed(self, topo) -> np.ndarray:
        """Returns 16-dim betweenness embedding."""
        bc = self.compute_betweenness(topo)

        # 64-dim summary
        sorted_bc = np.sort(bc)[::-1]
        summary = np.zeros(64, dtype=np.float32)
        n = min(len(sorted_bc), 60)
        summary[:n] = sorted_bc[:n]
        summary[60] = bc.mean() if len(bc) > 0 else 0.0
        summary[61] = bc.std()  if len(bc) > 0 else 0.0
        summary[62] = bc.max()  if len(bc) > 0 else 0.0
        summary[63] = float(len(bc)) / 256.0

        z = summary @ self._proj   # (16,)
        z = np.maximum(z, 0.0)
        norm = np.linalg.norm(z) + 1e-9
        return (z / norm).astype(np.float32)


# ---------------------------------------------------------------------------
# Risk Score Embedder
# ---------------------------------------------------------------------------
class RiskScoreEmbedder:
    """
    Computes a 16-dimensional embedding from load/capacity risk scores.

    For each line l:
        risk[l] = (sum of connected load) / (line_capacity_proxy + 1e-9)

    High risk → line is heavily loaded relative to its capacity → failure
    causes large load shedding.
    """

    OUT_DIM = 16

    def __init__(self, seed: int = 44):
        rng = np.random.RandomState(seed)
        self._proj = rng.randn(64, self.OUT_DIM).astype(np.float32) * np.sqrt(2.0 / 64)

    def compute_risk_scores(self, topo) -> np.ndarray:
        """
        Computes per-line risk scores based on connected load and line impedance.
        Returns (num_lines,) normalized risk scores.
        """
        N = topo.num_buses
        L = len(topo.lines)
        if L == 0:
            return np.zeros(1)

        # Bus load map
        bus_load = np.zeros(N)
        for bus, load in topo.loads.items():
            if 0 <= bus < N:
                bus_load[bus] = load["P_nom"]

        # Line capacity proxy: 1 / X (higher susceptance = more capacity)
        risk_scores = np.zeros(L, dtype=np.float32)
        for li, line in enumerate(topo.lines):
            f, t = line["from"], line["to"]
            capacity = 1.0 / (line["X"] + 1e-6)
            connected_load = 0.0
            if 0 <= f < N: connected_load += bus_load[f]
            if 0 <= t < N: connected_load += bus_load[t]
            risk_scores[li] = connected_load / (capacity + 1e-9)

        max_r = risk_scores.max() + 1e-9
        return risk_scores / max_r

    def embed(self, topo) -> np.ndarray:
        """Returns 16-dim risk score embedding."""
        risk = self.compute_risk_scores(topo)

        sorted_r = np.sort(risk)[::-1]
        summary = np.zeros(64, dtype=np.float32)
        n = min(len(sorted_r), 60)
        summary[:n] = sorted_r[:n]
        summary[60] = risk.mean() if len(risk) > 0 else 0.0
        summary[61] = risk.std()  if len(risk) > 0 else 0.0
        summary[62] = risk.max()  if len(risk) > 0 else 0.0
        summary[63] = float(len(risk)) / 256.0

        z = summary @ self._proj   # (16,)
        z = np.maximum(z, 0.0)
        norm = np.linalg.norm(z) + 1e-9
        return (z / norm).astype(np.float32)


# ---------------------------------------------------------------------------
# Criticality-Aware Encoder
# ---------------------------------------------------------------------------
class CriticalityAwareEncoder:
    """
    Main V10.6.2 encoder: combines trainable GNN with physics-based criticality.

    Output: z_final ∈ R^128, composed of:
        z_gnn  (64-dim) from TrainableGridEncoder
        z_ptdf (32-dim) from PTDFEmbedder
        z_bc   (16-dim) from BetweennessEmbedder
        z_risk (16-dim) from RiskScoreEmbedder
      → concat(128) → LayerNorm → L2-normalize → z_final(128)

    This makes z_final EXPLICITLY encode grid criticality, giving the policy
    the information it needs to learn to attack the most critical lines.
    """

    LATENT_DIM = 128

    def __init__(self, encoder_lr: float = 1e-3, seed: int = 42):
        from core.transfer.trainable_grid_encoder import TrainableGridEncoder

        # GNN: outputs 64-dim
        self.gnn = TrainableGridEncoder(lr=encoder_lr, seed=seed)
        # Criticality heads
        self.ptdf_embedder = PTDFEmbedder(seed=seed + 10)
        self.bc_embedder   = BetweennessEmbedder(seed=seed + 11)
        self.risk_embedder = RiskScoreEmbedder(seed=seed + 12)

        # Projection from GNN 128-dim output → 64-dim
        rng = np.random.RandomState(seed + 20)
        self.W_gnn_proj = (rng.randn(128, 64) * np.sqrt(2.0 / 128)).astype(np.float32)
        self.b_gnn_proj = np.zeros(64, dtype=np.float32)

        # Final LayerNorm (over 128-dim concat)
        self.ln_gamma = np.ones(128, dtype=np.float32)
        self.ln_beta  = np.zeros(128, dtype=np.float32)

        # Cache
        self._cache: Dict[str, Any] = {}

    def encode(self, topo, noise_std: float = 0.0) -> np.ndarray:
        """
        Produces a criticality-aware 128-dim latent vector.

        Args:
            topo     : Grid topology object
            noise_std: Optional Gaussian noise std for stochastic evaluation
        Returns:
            z_final: (128,) L2-normalized latent vector
        """
        # GNN embedding (128-dim from TrainableGridEncoder → project to 64)
        z_gnn_raw, gnn_cache = self.gnn.encode_with_cache(topo)  # (128,)
        z_gnn = np.maximum(z_gnn_raw @ self.W_gnn_proj + self.b_gnn_proj, 0.0)  # (64,)

        # Criticality embeddings (physics-based, not trainable in this version)
        z_ptdf = self.ptdf_embedder.embed(topo)    # (32,)
        z_bc   = self.bc_embedder.embed(topo)      # (16,)
        z_risk = self.risk_embedder.embed(topo)    # (16,)

        # Concatenate → 128-dim
        z_cat = np.concatenate([z_gnn, z_ptdf, z_bc, z_risk])  # (128,)

        # LayerNorm
        mu  = z_cat.mean()
        std = np.sqrt(z_cat.var() + 1e-8)
        z_norm = (z_cat - mu) / std
        z_ln = self.ln_gamma * z_norm + self.ln_beta              # (128,)

        # L2 normalize
        l2 = np.linalg.norm(z_ln) + 1e-9
        z_final = (z_ln / l2).astype(np.float32)

        # Optional noise for stochastic evaluation
        if noise_std > 0.0:
            z_final = z_final + np.random.randn(*z_final.shape).astype(np.float32) * noise_std
            z_final /= (np.linalg.norm(z_final) + 1e-9)

        # Store cache for backward
        self._cache = {
            "gnn_cache": gnn_cache, "z_gnn_raw": z_gnn_raw,
            "z_gnn": z_gnn, "z_ptdf": z_ptdf, "z_bc": z_bc, "z_risk": z_risk,
            "z_cat": z_cat, "mu": mu, "std": std, "z_norm": z_norm,
            "z_ln": z_ln, "l2": l2, "z_final": z_final,
        }
        return z_final

    def backward(self, dz_final: np.ndarray, clip: float = 0.5) -> None:
        """
        Backpropagates reward gradient through encoder.

        Only the GNN and projection weights are updated.
        Physics-based embedders (PTDF, BC, Risk) are kept fixed.
        """
        cache = self._cache
        if not cache or not cache.get("gnn_cache"):
            return

        # L2 normalization backward
        l2 = cache["l2"]
        z_ln = cache["z_ln"]
        dz_ln = (dz_final - np.dot(dz_final, cache["z_final"]) * cache["z_final"]) / l2

        # LayerNorm backward
        dln_gamma = (dz_ln * cache["z_norm"])
        dln_beta  = dz_ln
        dz_norm = dz_ln * self.ln_gamma
        n = len(dz_norm)
        std = cache["std"]
        dz_cat = (1.0 / (std * n)) * (
            n * dz_norm - dz_norm.sum() - cache["z_norm"] * (dz_norm * cache["z_norm"]).sum()
        )

        self.ln_gamma = np.clip(self.ln_gamma - 1e-3 * np.clip(dln_gamma, -clip, clip), 0.1, 10.0)
        self.ln_beta  = np.clip(self.ln_beta  - 1e-3 * np.clip(dln_beta,  -clip, clip), -5.0, 5.0)

        # Gradient flows only through z_gnn (first 64 dims)
        dz_gnn = dz_cat[:64]           # (64,)

        # Backward through GNN projection
        dpre_gnn = dz_gnn * (cache["z_gnn"] > 0).astype(np.float32)  # ReLU backward
        dW_gnn_proj = np.outer(cache["z_gnn_raw"], dpre_gnn)          # (128, 64)
        db_gnn_proj = dpre_gnn                                         # (64,)
        dz_gnn_raw = dpre_gnn @ self.W_gnn_proj.T                     # (128,)

        self.W_gnn_proj -= np.clip(1e-3 * dW_gnn_proj, -clip, clip)
        self.b_gnn_proj -= np.clip(1e-3 * db_gnn_proj, -clip, clip)

        # Propagate to GNN layers
        self.gnn.backward(dz_gnn_raw, cache["gnn_cache"], clip=clip)

    def get_top_k_targets(self, topo, k: int = 3) -> np.ndarray:
        """
        Returns the top-k most critical line indices using pure PTDF ranking.
        This is the 'Criticality-Guided' baseline (no learning).
        """
        return self.ptdf_embedder.top_k_critical_lines(topo, k=k)

    def save(self, path: str):
        """Save encoder weights."""
        self.gnn.save(path + "_gnn.npz")
        np.savez(path + "_crit.npz",
                 W_gnn_proj=self.W_gnn_proj, b_gnn_proj=self.b_gnn_proj,
                 ln_gamma=self.ln_gamma, ln_beta=self.ln_beta)

    def load(self, path: str):
        """Load encoder weights."""
        self.gnn.load(path + "_gnn.npz")
        d = np.load(path + "_crit.npz")
        self.W_gnn_proj = d["W_gnn_proj"]
        self.b_gnn_proj = d["b_gnn_proj"]
        self.ln_gamma = d["ln_gamma"]
        self.ln_beta  = d["ln_beta"]


if __name__ == "__main__":
    from core.digital_twin.multi_grid_topology import MultiGridTopology

    enc = CriticalityAwareEncoder()
    for g in ["ieee14", "ieee39", "ieee57", "ieee118"]:
        topo = MultiGridTopology(g)
        z = enc.encode(topo)
        top3 = enc.get_top_k_targets(topo, k=3)
        ptdf = enc.ptdf_embedder.compute_ptdf_scores(topo)
        print(f"{g}: z.shape={z.shape}, norm={np.linalg.norm(z):.4f}, "
              f"top3_ptdf_lines={top3}, ptdf_max={ptdf.max():.4f}")
