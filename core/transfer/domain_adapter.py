"""
Domain Adaptation Module — PYPY V10.6 Cross-Grid Transfer Learning.

Provides Maximum Mean Discrepancy (MMD) and Correlation Alignment (CORAL)
loss functions for measuring and minimizing domain shift between the latent
representations of different IEEE grid topologies.

These metrics are used in the V10.6 validation to:
  1. Quantify latent-space domain gap between source (IEEE39) and target grids.
  2. Visualize domain alignment before/after adaptation.
  3. Provide a soft loss penalty for training the transfer pathogen agent.

References:
  - Gretton et al., 2012: A Kernel Two-Sample Test (MMD)
  - Sun & Saenko, 2016: Deep CORAL: Correlation Alignment for Deep Domain Adaptation
"""
import numpy as np
from typing import Tuple


class DomainAdapter:
    """
    Domain adaptation metrics for latent grid embeddings.

    Supports:
      - Maximum Mean Discrepancy (MMD) with RBF kernel
      - Correlation Alignment (CORAL) loss
    """

    def __init__(self, bandwidth: float = 1.0):
        """
        Args:
            bandwidth: RBF kernel bandwidth parameter σ for MMD computation.
                       If None, uses median heuristic.
        """
        self.bandwidth = bandwidth

    # ------------------------------------------------------------------
    # MMD: Maximum Mean Discrepancy
    # ------------------------------------------------------------------
    def _rbf_kernel(self, X: np.ndarray, Y: np.ndarray, sigma: float) -> np.ndarray:
        """
        Computes the RBF (Gaussian) kernel between rows of X and Y.
        K(x, y) = exp(-||x - y||^2 / (2*sigma^2))
        """
        XX = np.sum(X ** 2, axis=1, keepdims=True)  # (n, 1)
        YY = np.sum(Y ** 2, axis=1, keepdims=True)  # (m, 1)
        XY = X @ Y.T                                 # (n, m)
        sq_dists = XX + YY.T - 2 * XY               # (n, m)
        return np.exp(-sq_dists / (2.0 * sigma ** 2 + 1e-9))

    def _median_bandwidth(self, X: np.ndarray, Y: np.ndarray) -> float:
        """Computes the median heuristic bandwidth from combined data."""
        combined = np.vstack([X, Y])
        n = combined.shape[0]
        # Sample at most 200 pairs for efficiency
        idx = np.random.choice(n, min(n, 200), replace=False)
        sub = combined[idx]
        diffs = sub[:, None, :] - sub[None, :, :]   # (k, k, d)
        sq_dists = np.sum(diffs ** 2, axis=-1)       # (k, k)
        # Median of upper triangle
        triu_vals = sq_dists[np.triu_indices(sub.shape[0], k=1)]
        med = np.median(triu_vals)
        return float(np.sqrt(med / 2.0)) if med > 1e-12 else 1.0

    def mmd_loss(self, z_source: np.ndarray, z_target: np.ndarray) -> float:
        """
        Computes the Maximum Mean Discrepancy (MMD) between source and target
        latent representations using an RBF kernel.

        MMD²(S, T) = E[k(s,s')] - 2E[k(s,t)] + E[k(t,t')]

        Args:
            z_source: Latent embeddings of source domain, shape (n, d)
            z_target: Latent embeddings of target domain, shape (m, d)
        Returns:
            mmd: Scalar MMD distance (≥ 0).
        """
        z_source = np.atleast_2d(z_source).astype(np.float64)
        z_target = np.atleast_2d(z_target).astype(np.float64)

        sigma = self._median_bandwidth(z_source, z_target) if self.bandwidth is None else self.bandwidth

        K_ss = self._rbf_kernel(z_source, z_source, sigma)
        K_tt = self._rbf_kernel(z_target, z_target, sigma)
        K_st = self._rbf_kernel(z_source, z_target, sigma)

        n, m = z_source.shape[0], z_target.shape[0]
        mmd_sq = (K_ss.sum() / (n * n)
                  - 2 * K_st.sum() / (n * m)
                  + K_tt.sum() / (m * m))

        return float(max(mmd_sq, 0.0))

    # ------------------------------------------------------------------
    # CORAL: Correlation Alignment
    # ------------------------------------------------------------------
    def coral_loss(self, z_source: np.ndarray, z_target: np.ndarray) -> float:
        """
        Computes the CORAL loss between source and target latent distributions.
        Measures the Frobenius norm of the difference between covariance matrices.

        L_CORAL = (1 / 4d²) ||C_S - C_T||²_F

        Args:
            z_source: Latent embeddings of source domain, shape (n, d)
            z_target: Latent embeddings of target domain, shape (m, d)
        Returns:
            coral: Scalar CORAL loss (≥ 0).
        """
        z_source = np.atleast_2d(z_source).astype(np.float64)
        z_target = np.atleast_2d(z_target).astype(np.float64)

        d = z_source.shape[1]

        # Covariance matrices
        C_s = np.cov(z_source.T) if z_source.shape[0] > 1 else np.eye(d)
        C_t = np.cov(z_target.T) if z_target.shape[0] > 1 else np.eye(d)

        diff = C_s - C_t
        coral = np.sum(diff ** 2) / (4.0 * d * d)

        return float(max(coral, 0.0))

    # ------------------------------------------------------------------
    # Unified alignment interface
    # ------------------------------------------------------------------
    def align(self, z_source: np.ndarray, z_target: np.ndarray,
              method: str = "mmd") -> float:
        """
        Computes domain discrepancy using the specified method.

        Args:
            z_source: Source latent matrix (n, d)
            z_target: Target latent matrix (m, d)
            method: "mmd" or "coral"
        Returns:
            discrepancy: Scalar ≥ 0
        """
        if method == "mmd":
            return self.mmd_loss(z_source, z_target)
        elif method == "coral":
            return self.coral_loss(z_source, z_target)
        else:
            raise ValueError(f"Unknown alignment method '{method}'. Use 'mmd' or 'coral'.")

    def alignment_matrix(self, embeddings: dict, method: str = "mmd") -> Tuple[np.ndarray, list]:
        """
        Computes a pairwise alignment matrix between multiple grid embeddings.

        Args:
            embeddings: dict {grid_name: z_matrix (n, d)}
            method: "mmd" or "coral"
        Returns:
            matrix: (n_grids, n_grids) alignment distance matrix
            labels: list of grid names
        """
        labels = list(embeddings.keys())
        n = len(labels)
        matrix = np.zeros((n, n))

        for i, g1 in enumerate(labels):
            for j, g2 in enumerate(labels):
                if i != j:
                    matrix[i, j] = self.align(
                        np.atleast_2d(embeddings[g1]),
                        np.atleast_2d(embeddings[g2]),
                        method=method
                    )

        return matrix, labels


if __name__ == "__main__":
    np.random.seed(42)
    adapter = DomainAdapter()

    # Simulate two grid latent spaces
    z_s = np.random.randn(10, 128)
    z_t = np.random.randn(8, 128) + 0.5  # slightly shifted

    mmd = adapter.mmd_loss(z_s, z_t)
    coral = adapter.coral_loss(z_s, z_t)
    print(f"MMD loss:   {mmd:.6f}")
    print(f"CORAL loss: {coral:.6f}")
