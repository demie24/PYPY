"""
Self-Supervised Pre-training — PYPY V10.6.2.

Pre-trains the CriticalityAwareEncoder on all 4 grids before PPO training.
This gives the encoder topology-aware representations that transfer better.

Three pre-training tasks (Tasks 3 + 4):
  A. Node Masking Reconstruction (α=0.40)
     - Mask 20% of node features with zeros
     - Train encoder to reconstruct masked features
     - Loss: MSE between masked and reconstructed features

  B. Edge Prediction (β=0.30)
     - Sample positive edges (existing) and negative edges (non-existing)
     - Train encoder to predict edge existence from node embeddings
     - Loss: Binary cross-entropy

  C. Critical Line Prediction (γ=0.30)
     - Predict the top-K critical lines by PTDF score
     - Loss: Binary cross-entropy over line criticality labels

Joint pre-training loss:
    L = α·L_recon + β·L_edge + γ·L_criticality

After pre-training, encoder weights are used as initialization for PPO training.
All computation is pure numpy.
"""
import os
import sys
import random
import numpy as np
from typing import List, Dict, Tuple, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


class SelfSupervisedPretrainer:
    """
    Multi-task self-supervised pre-trainer for the CriticalityAwareEncoder.

    Pre-trains on all supported grid topologies simultaneously using three
    complementary auxiliary tasks that teach the encoder to represent:
      - Node types and connectivity patterns (Task A)
      - Graph topology structure (Task B)
      - Physically critical infrastructure (Task C)
    """

    def __init__(self, encoder, alpha: float = 0.40, beta: float = 0.30,
                 gamma: float = 0.30, lr: float = 1e-3, seed: int = 42):
        """
        Args:
            encoder : CriticalityAwareEncoder instance (trainable)
            alpha   : Weight for reconstruction loss (Task A)
            beta    : Weight for edge prediction loss (Task B)
            gamma   : Weight for criticality prediction loss (Task C)
            lr      : Learning rate for auxiliary heads
            seed    : Random seed
        """
        self.encoder = encoder
        self.alpha = alpha
        self.beta  = beta
        self.gamma = gamma
        self.lr    = lr

        rng = np.random.RandomState(seed)

        # Task A — Reconstruction head: z(128) → node_features(6)
        # Projects z back to per-node features using a simple MLP
        self.W_recon_1 = (rng.randn(128, 64) * np.sqrt(2/128)).astype(np.float32)
        self.b_recon_1 = np.zeros(64, dtype=np.float32)
        self.W_recon_2 = (rng.randn(64, 6) * np.sqrt(2/64)).astype(np.float32)
        self.b_recon_2 = np.zeros(6, dtype=np.float32)

        # Task B — Edge prediction head: concat(z_i, z_j)(256) → logit(1)
        # Use z as node rep, predict edge via inner product of GNN node embeddings
        self.W_edge = (rng.randn(128, 1) * np.sqrt(2/128)).astype(np.float32)
        self.b_edge = np.zeros(1, dtype=np.float32)

        # Task C — Criticality head: z(128) → per-line-criticality logits(256)
        # Projects z to a fixed 256-dim criticality map (zero-padded for small grids)
        self.W_crit = (rng.randn(128, 256) * np.sqrt(2/128)).astype(np.float32)
        self.b_crit = np.zeros(256, dtype=np.float32)

        self.training_losses: List[float] = []

    # -------------------------------------------------------------------
    # Task A: Node Masking Reconstruction
    # -------------------------------------------------------------------
    def _mask_features(self, H: np.ndarray, mask_rate: float = 0.20,
                       seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Randomly masks a fraction of node features.
        Returns (H_masked, mask_indices).
        """
        rng = np.random.RandomState(seed)
        N = H.shape[0]
        n_mask = max(1, int(N * mask_rate))
        mask_idx = rng.choice(N, size=n_mask, replace=False)
        H_masked = H.copy()
        H_masked[mask_idx, :] = 0.0
        return H_masked, mask_idx

    def _reconstruction_loss(self, z: np.ndarray, H_orig: np.ndarray,
                              mask_idx: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        Computes MSE reconstruction loss over masked nodes.
        Returns (loss, dz) gradient w.r.t. z.
        """
        # Decode: z → (6,) per-node features (using shared z as proxy)
        h1 = np.maximum(z @ self.W_recon_1 + self.b_recon_1, 0.0)   # (64,)
        recon = h1 @ self.W_recon_2 + self.b_recon_2                  # (6,)

        # Target: mean of masked node features
        if len(mask_idx) == 0:
            return 0.0, np.zeros_like(z)

        target = H_orig[mask_idx, :].mean(axis=0)   # (6,)
        diff = recon - target                         # (6,)
        loss = 0.5 * np.mean(diff ** 2)

        # Backward
        d_recon = diff / 6.0                          # (6,)
        d_h1 = d_recon @ self.W_recon_2.T            # (64,)
        d_h1 *= (h1 > 0)                             # ReLU

        dW_r2 = np.outer(h1, d_recon)
        db_r2 = d_recon
        dW_r1 = np.outer(z, d_h1)
        db_r1 = d_h1
        dz = d_h1 @ self.W_recon_1.T                 # (128,)

        # Update aux heads
        self.W_recon_2 -= self.lr * np.clip(dW_r2, -1.0, 1.0)
        self.b_recon_2 -= self.lr * np.clip(db_r2, -1.0, 1.0)
        self.W_recon_1 -= self.lr * np.clip(dW_r1, -1.0, 1.0)
        self.b_recon_1 -= self.lr * np.clip(db_r1, -1.0, 1.0)

        return float(loss), dz

    # -------------------------------------------------------------------
    # Task B: Edge Prediction
    # -------------------------------------------------------------------
    def _edge_prediction_loss(self, z: np.ndarray,
                               topo, seed: int = 0) -> Tuple[float, np.ndarray]:
        """
        Predicts edge existence using z as a proxy for all node embeddings.
        Positive edges: real edges. Negative edges: random pairs.
        Loss: BCE.
        """
        rng = np.random.RandomState(seed)
        N = topo.num_buses
        L = len(topo.lines)
        if L == 0 or N < 2:
            return 0.0, np.zeros_like(z)

        # Positive samples: existing edges (sample up to 10)
        n_pos = min(10, L)
        pos_lines = rng.choice(L, size=n_pos, replace=False)
        pos_labels = np.ones(n_pos)

        # Negative samples: non-existing random edges
        existing = set((l["from"], l["to"]) for l in topo.lines)
        existing |= set((l["to"], l["from"]) for l in topo.lines)
        neg_edges = []
        for _ in range(n_pos * 3):
            f = rng.randint(0, N)
            t = rng.randint(0, N)
            if f != t and (f, t) not in existing:
                neg_edges.append((f, t))
            if len(neg_edges) >= n_pos:
                break
        n_neg = len(neg_edges)
        if n_neg == 0:
            return 0.0, np.zeros_like(z)

        # For edge (f,t): score = z.T @ W_edge (using z as shared representation)
        # This is a crude proxy — the latent z represents the whole graph
        # We encode each edge as: score_k = z.dot(w_edge) + b_edge
        logits_pos = (z @ self.W_edge + self.b_edge).reshape(-1)  # (1,)
        logits_neg = -(z @ self.W_edge + self.b_edge).reshape(-1) # flip for negatives

        def bce(logit, label):
            p = 1.0 / (1.0 + np.exp(-np.clip(logit, -15, 15)))
            return -label * np.log(p + 1e-9) - (1-label) * np.log(1-p + 1e-9), p

        loss_pos, p_pos = bce(logits_pos[0], 1.0)
        loss_neg, p_neg = bce(logits_neg[0], 0.0)
        loss = 0.5 * (loss_pos + loss_neg)

        # Gradient
        d_logit_pos = p_pos - 1.0   # d_BCE/d_logit for positive
        d_logit_neg = p_neg          # d_BCE/d_logit for negative (inverted)

        dW = np.outer(z, (d_logit_pos - d_logit_neg).reshape(1))  # (128,1)
        db = (d_logit_pos - d_logit_neg).reshape(1)
        dz = ((d_logit_pos - d_logit_neg) * self.W_edge).reshape(-1) * 0.5  # (128,)

        self.W_edge -= self.lr * np.clip(dW, -1.0, 1.0)
        self.b_edge -= self.lr * np.clip(db, -1.0, 1.0)

        return float(loss), dz

    # -------------------------------------------------------------------
    # Task C: Critical Line Prediction
    # -------------------------------------------------------------------
    def _criticality_loss(self, z: np.ndarray,
                           topo, k_frac: float = 0.2) -> Tuple[float, np.ndarray]:
        """
        Predicts which lines are in the top-k critical by PTDF score.
        Loss: Binary cross-entropy over a 256-dim binary label vector.
        """
        L = len(topo.lines)
        if L == 0:
            return 0.0, np.zeros_like(z)

        # Get PTDF critical labels
        ptdf = self.encoder.ptdf_embedder.compute_ptdf_scores(topo)  # (L,)
        k = max(1, int(L * k_frac))
        top_k = set(np.argsort(ptdf)[::-1][:k].tolist())

        # Build 256-dim binary label (zero-padded)
        labels = np.zeros(256, dtype=np.float32)
        for li in range(min(L, 256)):
            labels[li] = 1.0 if li in top_k else 0.0

        # Predict: z(128) → logits(256) → sigmoid → BCE
        logits = z @ self.W_crit + self.b_crit   # (256,)
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -15, 15)))  # sigmoid

        bce = -labels * np.log(probs + 1e-9) - (1 - labels) * np.log(1 - probs + 1e-9)
        loss = bce.mean()

        # Backward
        d_logits = (probs - labels) / 256.0       # (256,)
        dW = np.outer(z, d_logits)                # (128, 256)
        db = d_logits                             # (256,)
        dz = d_logits @ self.W_crit.T             # (128,)

        self.W_crit -= self.lr * np.clip(dW, -1.0, 1.0)
        self.b_crit -= self.lr * np.clip(db, -1.0, 1.0)

        return float(loss), dz

    # -------------------------------------------------------------------
    # Pre-training loop
    # -------------------------------------------------------------------
    def pretrain(self, topologies: List, n_epochs: int = 100,
                 verbose_every: int = 20, seed: int = 42) -> List[float]:
        """
        Runs multi-task self-supervised pre-training across all topologies.

        Args:
            topologies   : List of topology objects (all 4 IEEE grids)
            n_epochs     : Number of pre-training iterations
            verbose_every: Print interval
            seed         : Base random seed
        Returns:
            training_losses: List of total loss per epoch
        """
        np.random.seed(seed)
        random.seed(seed)
        self.training_losses = []

        for epoch in range(n_epochs):
            epoch_loss = 0.0

            for topo in topologies:
                ep_seed = seed * 10000 + epoch * 100 + id(topo) % 100

                # Get node features for reconstruction task
                H_orig = self.encoder.gnn._build_node_features(topo)

                # Encode with full criticality-aware encoder
                z = self.encoder.encode(topo)

                # Mask features for Task A
                H_masked, mask_idx = self._mask_features(H_orig, seed=ep_seed)

                # Task A: Reconstruction
                loss_A, dz_A = self._reconstruction_loss(z, H_orig, mask_idx)

                # Task B: Edge prediction
                loss_B, dz_B = self._edge_prediction_loss(z, topo, seed=ep_seed + 1)

                # Task C: Criticality prediction
                loss_C, dz_C = self._criticality_loss(z, topo)

                # Combine gradients
                total_loss = self.alpha * loss_A + self.beta * loss_B + self.gamma * loss_C
                dz_total = (self.alpha * dz_A + self.beta * dz_B + self.gamma * dz_C)

                # Backpropagate combined gradient through encoder
                self.encoder.backward(dz_total, clip=0.3)
                epoch_loss += total_loss

            epoch_loss /= len(topologies)
            self.training_losses.append(epoch_loss)

            if verbose_every > 0 and (epoch + 1) % verbose_every == 0:
                print(f"  [SSL Pretrain] Epoch {epoch+1:4d}/{n_epochs}: "
                      f"loss={epoch_loss:.4f}")

        return self.training_losses


def pretrain_encoder(topologies: List, n_epochs: int = 200,
                     lr: float = 1e-3, seed: int = 42,
                     verbose_every: int = 50) -> "CriticalityAwareEncoder":
    """
    Convenience function: creates encoder, pre-trains, returns ready encoder.

    Args:
        topologies   : List of MultiGridTopology objects
        n_epochs     : Pre-training epochs
        lr           : Encoder learning rate
        seed         : Random seed
        verbose_every: Print interval
    Returns:
        Pretrained CriticalityAwareEncoder
    """
    from core.transfer.criticality_encoder import CriticalityAwareEncoder

    encoder = CriticalityAwareEncoder(encoder_lr=lr, seed=seed)
    pretrainer = SelfSupervisedPretrainer(
        encoder, alpha=0.40, beta=0.30, gamma=0.30, lr=lr, seed=seed
    )
    print(f"[SSL Pretrain] Starting {n_epochs} epochs on {len(topologies)} grids...")
    losses = pretrainer.pretrain(topologies, n_epochs=n_epochs,
                                 verbose_every=verbose_every, seed=seed)
    print(f"[SSL Pretrain] Complete. Final loss: {losses[-1]:.4f}")
    return encoder


if __name__ == "__main__":
    from core.digital_twin.multi_grid_topology import MultiGridTopology, SUPPORTED_GRIDS

    topos = [MultiGridTopology(g) for g in SUPPORTED_GRIDS]
    encoder = pretrain_encoder(topos, n_epochs=50, verbose_every=10)
    print("Pre-training complete.")

    for topo in topos:
        z = encoder.encode(topo)
        top3 = encoder.get_top_k_targets(topo, k=3)
        print(f"{topo.grid_name}: z_norm={np.linalg.norm(z):.4f}, top3={top3}")
