"""
Stealth FDIA Optimizer — PYPY V10.7.

Optimizes the FDIA attack vector to minimize detection probability while
maximizing attack impact (islanding / load shed).

Multi-objective loss:
    L = α * PINN_residual + β * GNN_risk + γ * Trust_loss

Where:
  PINN_residual: measures how much the spoofed measurements violate AC power
                 flow equations (physics-informed neural network proxy).
                 Lower → harder for PINN detector to flag.

  GNN_risk:      graph neural network anomaly score — deviation from
                 learned graph structure patterns.
                 Lower → harder for GNN detector to flag.

  Trust_loss:    KL divergence between spoofed and nominal measurement
                 distributions (trust region constraint).
                 Lower → measurements are indistinguishable from normal.

Optimizer: projected gradient descent with momentum (pure NumPy).
Constraint set: IEEE stealth bounds (L∞ projection).
"""
import os
import sys
import numpy as np
from typing import Dict, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from core.adversarial.zero_parameter_fdia import (
    ZeroParameterFDIA, VOLTAGE_STEALTH_BOUND, POWER_STEALTH_BOUND, FREQUENCY_STEALTH_BOUND
)


# ---------------------------------------------------------------------------
# PINN residual proxy (simplified AC power flow equations)
# ---------------------------------------------------------------------------

class PINNResidualProxy:
    """
    Lightweight PINN-like AC power flow residual calculator.

    Simulates what a physics-informed detector would compute:
      F(V, P) = |P_mismatch|  (power balance residual)
    
    A real PINN learns F(x) → 0 for valid operating points.
    This proxy implements the DC power balance residual.
    """

    def __init__(self, topo, noise_std: float = 0.002, seed: int = 42):
        self.topo = topo
        self.noise_std = noise_std
        self.rng = np.random.RandomState(seed)
        self._build_sensitivity()
        
        # Build nominal power injections vector from topology gen/load
        n = self.topo.num_buses
        self.P_nom = np.zeros(n, dtype=np.float32)
        for bus, gen_info in self.topo.generators.items():
            self.P_nom[bus] += gen_info.get("P_nom", 0.0)
        for bus, load_info in self.topo.loads.items():
            self.P_nom[bus] -= load_info.get("P_nom", 0.0)

    def _build_sensitivity(self):
        """Build simplified B matrix for power flow residual computation."""
        n = self.topo.num_buses
        self.B = np.zeros((n, n), dtype=np.float32)
        for line in self.topo.lines:
            f, t = line["from"], line["to"]
            x = line.get("X", 0.1)
            b = 1.0 / max(abs(x), 1e-6)
            self.B[f, f] += b
            self.B[t, t] += b
            self.B[f, t] -= b
            self.B[t, f] -= b

    def residual(self, V_spoofed: np.ndarray, P_inj_spoofed: np.ndarray) -> float:
        """
        Compute power flow residual for spoofed measurements.

        DC approximation: delta_P_inj = B @ delta_theta
        Residual = ||(P_inj_spoofed - P_nom) - B @ theta_estimated||₂ / n_buses

        Higher residual → more detectable by PINN.
        """
        n = self.topo.num_buses
        # Estimate theta from spoofed V (angle ≈ 1 - V_pu approximation)
        theta_est = np.clip(1.0 - V_spoofed, -0.3, 0.3).astype(np.float32)

        # Expected power injection deviation from estimated angles
        P_expected = self.B @ theta_est

        # Incremental Residual
        mismatch = (P_inj_spoofed[:n] - self.P_nom[:n]) - P_expected[:n]
        residual = float(np.linalg.norm(mismatch)) / n

        # Add detector noise (PINN has finite precision)
        residual += self.rng.randn() * self.noise_std

        return max(0.0, residual)

    def bypass_probability(self, residual: float, threshold: float = 0.05) -> float:
        """P(bypass PINN detector) = P(residual < threshold)."""
        # Model PINN detection as: detected if residual > threshold
        # Bypass if residual ≤ threshold
        return float(residual <= threshold)

    def gradient_wrt_V(self, V: np.ndarray, P_inj: np.ndarray) -> np.ndarray:
        """Gradient of residual w.r.t. V (for projected gradient descent)."""
        n = self.topo.num_buses
        theta_est = np.clip(1.0 - V, -0.3, 0.3)
        P_expected = self.B @ theta_est
        mismatch = (P_inj[:n] - P_expected[:n]) / (n + 1e-9)
        # d(residual)/d(mismatch) → d(mismatch)/d(theta) = -B
        # d(theta)/d(V) = -1  (from theta = 1 - V)
        # Chain: grad = B^T @ mismatch / norm
        norm = np.linalg.norm(mismatch) + 1e-9
        grad_P = mismatch / norm
        # Back through B @ theta: d(P_expected)/d(V) = B @ (-I) = -B
        grad_V = self.B.T @ grad_P
        return grad_V.astype(np.float32)


# ---------------------------------------------------------------------------
# GNN anomaly score proxy
# ---------------------------------------------------------------------------

class GNNAnomalyProxy:
    """
    GNN anomaly score proxy.

    A GNN detector learns to flag measurements inconsistent with
    graph topology. This proxy estimates the anomaly score as:
    
      score = ||f(x_spoofed) - f(x_nom)||₂
    
    where f() is a graph aggregation function (mean neighborhood feature).
    Higher score → more detectable.
    """

    def __init__(self, topo, seed: int = 42):
        self.topo = topo
        self.rng = np.random.RandomState(seed)
        self._build_adjacency()

    def _build_adjacency(self):
        """Build normalized adjacency for GNN aggregation."""
        n = self.topo.num_buses
        A = np.zeros((n, n), dtype=np.float32)
        for line in self.topo.lines:
            f, t = line["from"], line["to"]
            A[f, t] = 1.0
            A[t, f] = 1.0

        # Degree normalization
        deg = A.sum(axis=1, keepdims=True) + 1e-9
        self.A_hat = A / deg   # normalized adjacency

    def anomaly_score(self, V_spoofed: np.ndarray, P_inj_spoofed: np.ndarray,
                       V_nom: np.ndarray, P_nom: np.ndarray) -> float:
        """
        Compute GNN anomaly score.

        Score = ||A_hat @ V_sp - A_hat @ V_nom||₂ / n_buses
        (deviation in neighborhood-averaged voltage)
        """
        n = self.topo.num_buses
        # Graph-aggregated features
        agg_sp  = self.A_hat @ V_spoofed[:n]
        agg_nom = self.A_hat @ V_nom[:n]
        score = float(np.linalg.norm(agg_sp - agg_nom)) / n
        return max(0.0, score)

    def bypass_probability(self, score: float, threshold: float = 0.01) -> float:
        """P(bypass GNN detector) = P(score < threshold)."""
        return float(score <= threshold)

    def gradient_wrt_V(self, V_spoofed: np.ndarray, V_nom: np.ndarray) -> np.ndarray:
        """Gradient of anomaly score w.r.t. V_spoofed."""
        n = self.topo.num_buses
        diff = self.A_hat @ V_spoofed[:n] - self.A_hat @ V_nom[:n]
        norm = np.linalg.norm(diff) + 1e-9
        grad = self.A_hat.T @ (diff / norm) / n
        return grad.astype(np.float32)


# ---------------------------------------------------------------------------
# Trust loss (measurement distribution divergence)
# ---------------------------------------------------------------------------

def trust_loss(V_spoofed: np.ndarray, V_nom: np.ndarray,
               P_sp: np.ndarray, P_nom: np.ndarray,
               sigma_v: float = 0.005, sigma_p: float = 0.01) -> float:
    """
    Approximate KL divergence between spoofed and nominal measurement
    distributions (both modeled as Gaussian).

    KL(N(μ_sp, σ²) || N(μ_nom, σ²)) = ||μ_sp - μ_nom||₂² / (2σ²)
    """
    n = min(len(V_spoofed), len(V_nom))
    kl_v = float(np.sum((V_spoofed[:n] - V_nom[:n])**2)) / (2 * sigma_v**2 * n)
    m = min(len(P_sp), len(P_nom))
    kl_p = float(np.sum((P_sp[:m] - P_nom[:m])**2)) / (2 * sigma_p**2 * m)
    return 0.5 * kl_v + 0.5 * kl_p


def trust_loss_gradient_V(V_spoofed: np.ndarray, V_nom: np.ndarray,
                            sigma_v: float = 0.005) -> np.ndarray:
    """Gradient of trust_loss w.r.t. V_spoofed."""
    n = len(V_spoofed)
    return ((V_spoofed - V_nom) / (sigma_v**2 * n)).astype(np.float32)


# ---------------------------------------------------------------------------
# Main stealth optimizer
# ---------------------------------------------------------------------------

class StealthFDIAOptimizer:
    """
    Projected gradient descent optimizer for stealth FDIA.

    Minimizes: L = α * PINN_residual + β * GNN_risk + γ * Trust_loss

    Subject to: ||δV||∞ ≤ v_bound
                ||δP||∞ ≤ p_bound  
                ||δf||  ≤ f_bound

    Pure NumPy; no external ML libraries.
    """

    def __init__(self, topo,
                 alpha: float = 0.40,
                 beta:  float = 0.35,
                 gamma: float = 0.25,
                 lr:    float = 1e-3,
                 n_iter: int = 100,
                 momentum: float = 0.90,
                 seed:  int = 42):
        """
        Args:
            alpha:    weight for PINN residual
            beta:     weight for GNN anomaly score
            gamma:    weight for Trust loss (KL divergence)
            lr:       learning rate for projected gradient descent
            n_iter:   number of optimization iterations
            momentum: SGD momentum coefficient
            seed:     random seed
        """
        self.topo = topo
        self.alpha = alpha
        self.beta  = beta
        self.gamma = gamma
        self.lr    = lr
        self.n_iter = n_iter
        self.momentum = momentum
        self.rng = np.random.RandomState(seed)

        # Build proxy detectors
        self.pinn = PINNResidualProxy(topo, seed=seed)
        self.gnn  = GNNAnomalyProxy(topo, seed=seed)

        # Bounds
        self.v_bound = VOLTAGE_STEALTH_BOUND
        self.p_bound = POWER_STEALTH_BOUND
        self.f_bound = FREQUENCY_STEALTH_BOUND

    def optimize(self,
                  attack_init: Dict,
                  V_nom: np.ndarray,
                  P_nom: np.ndarray,
                  verbose: bool = False) -> Dict:
        """
        Optimize the attack vector to minimize detection loss.

        Args:
            attack_init: Initial attack dict from ZeroParameterFDIA.generate_fdia()
            V_nom:       Nominal voltage vector
            P_nom:       Nominal power injection vector

        Returns:
            Optimized attack dict with additional keys:
              'loss_history'    : (n_iter,) array of total loss
              'pinn_history'    : (n_iter,) PINN residuals
              'gnn_history'     : (n_iter,) GNN scores
              'trust_history'   : (n_iter,) Trust losses
              'final_loss'      : final total loss
              'pinn_bypass_prob': P(evade PINN)
              'gnn_bypass_prob' : P(evade GNN)
        """
        # Initialize optimization variables
        V_opt = attack_init["V_spoofed"].copy()
        P_opt = attack_init["P_line_spoofed"].copy()
        P_inj_opt = attack_init["P_inj_spoofed"].copy()

        # Momentum terms
        v_mom = np.zeros_like(V_opt)
        p_mom = np.zeros_like(P_opt)

        loss_hist  = np.zeros(self.n_iter)
        pinn_hist  = np.zeros(self.n_iter)
        gnn_hist   = np.zeros(self.n_iter)
        trust_hist = np.zeros(self.n_iter)

        # Adaptive learning rate (RMSProp-like)
        v_grad_sq = np.ones_like(V_opt) * 1e-8
        p_grad_sq = np.ones_like(P_opt) * 1e-8
        eps_rms = 1e-8
        decay = 0.9

        for it in range(self.n_iter):
            # --- Forward pass ---
            pinn_res  = self.pinn.residual(V_opt, P_inj_opt)
            gnn_score = self.gnn.anomaly_score(V_opt, P_inj_opt, V_nom, P_nom)
            P_line_nom_val = self.P_line_nom(P_opt)
            t_loss    = trust_loss(V_opt, V_nom, P_opt, P_line_nom_val)
            total_loss = self.alpha * pinn_res + self.beta * gnn_score + self.gamma * t_loss

            loss_hist[it]  = total_loss
            pinn_hist[it]  = pinn_res
            gnn_hist[it]   = gnn_score
            trust_hist[it] = t_loss

            if verbose and it % 20 == 0:
                print(f"  [StealthOpt] iter {it:3d}/{self.n_iter}: "
                      f"L={total_loss:.5f} PINN={pinn_res:.5f} "
                      f"GNN={gnn_score:.5f} Trust={t_loss:.5f}")

            # --- Compute gradients ---
            grad_V_pinn  = self.pinn.gradient_wrt_V(V_opt, P_inj_opt)
            grad_V_gnn   = self.gnn.gradient_wrt_V(V_opt, V_nom)
            grad_V_trust = trust_loss_gradient_V(V_opt, V_nom)

            grad_V = (self.alpha  * grad_V_pinn
                    + self.beta   * grad_V_gnn
                    + self.gamma  * grad_V_trust)

            # P gradient: only trust loss affects P directly
            n_buses = self.topo.num_buses
            n_lines = len(self.topo.lines)
            grad_P = np.zeros_like(P_opt)
            m = min(n_lines, len(P_line_nom_val))
            grad_P[:m] = self.gamma * (P_opt[:m] - P_line_nom_val[:m]) / (0.01**2 * m)

            # --- Clip gradients ---
            grad_V = np.clip(grad_V, -1.0, 1.0)
            grad_P = np.clip(grad_P, -1.0, 1.0)

            # --- RMSProp adaptive update ---
            v_grad_sq = decay * v_grad_sq + (1 - decay) * grad_V**2
            p_grad_sq = decay * p_grad_sq + (1 - decay) * grad_P**2
            lr_v = self.lr / (np.sqrt(v_grad_sq) + eps_rms)
            lr_p = self.lr / (np.sqrt(p_grad_sq) + eps_rms)

            # --- Momentum update ---
            v_mom = self.momentum * v_mom - lr_v * grad_V
            p_mom = self.momentum * p_mom - lr_p * grad_P

            # Backtracking line search to guarantee monotonic loss descent
            step_scale = 1.0
            accepted = False
            for backtrack in range(8):
                V_next = V_opt + step_scale * v_mom
                P_next = P_opt + step_scale * p_mom

                # Projection onto stealth constraints
                delta_V = V_next - V_nom
                delta_V = np.clip(delta_V, -self.v_bound, self.v_bound)
                V_next = V_nom + delta_V
                V_next = np.clip(V_next, 0.90, 1.10)

                P_next = np.clip(P_next, self.P_line_nom(P_next) - self.p_bound,
                                         self.P_line_nom(P_next) + self.p_bound)

                pinn_next = self.pinn.residual(V_next, P_inj_opt)
                gnn_next  = self.gnn.anomaly_score(V_next, P_inj_opt, V_nom, P_nom)
                t_loss_next = trust_loss(V_next, V_nom, P_next, self.P_line_nom(P_next))
                loss_next = self.alpha * pinn_next + self.beta * gnn_next + self.gamma * t_loss_next

                if loss_next <= total_loss + 1e-6:
                    V_opt = V_next
                    P_opt = P_next
                    accepted = True
                    break
                step_scale *= 0.5

            if not accepted:
                # Reset momentum on rejection to try gradient direction next step
                v_mom = np.zeros_like(V_opt)
                p_mom = np.zeros_like(P_opt)

        # --- Final metrics ---
        final_pinn  = self.pinn.residual(V_opt, P_inj_opt)
        final_gnn   = self.gnn.anomaly_score(V_opt, P_inj_opt, V_nom, P_nom)
        final_trust = trust_loss(V_opt, V_nom, P_opt, self.P_line_nom(P_opt))
        final_loss  = self.alpha * final_pinn + self.beta * final_gnn + self.gamma * final_trust

        pinn_bypass = self.pinn.bypass_probability(final_pinn, threshold=0.05)
        gnn_bypass  = self.gnn.bypass_probability(final_gnn,   threshold=0.015)

        result = dict(attack_init)  # copy input
        result.update({
            "V_spoofed":        V_opt,
            "P_line_spoofed":   P_opt,
            "loss_history":     loss_hist,
            "pinn_history":     pinn_hist,
            "gnn_history":      gnn_hist,
            "trust_history":    trust_hist,
            "final_loss":       final_loss,
            "final_pinn":       final_pinn,
            "final_gnn":        final_gnn,
            "final_trust":      final_trust,
            "pinn_bypass_prob": pinn_bypass,
            "gnn_bypass_prob":  gnn_bypass,
        })
        return result

    def P_line_nom(self, _):
        """Helper to get nominal P_line (returned from topo)."""
        # Extract from each line's DC flow approximation
        return np.array([
            1.0 / max(abs(l.get("X", 0.1)), 1e-6) * 0.01
            for l in self.topo.lines
        ], dtype=np.float32)

    def batch_optimize(self,
                        attacks: list,
                        V_nom: np.ndarray,
                        P_nom: np.ndarray) -> list:
        """Optimize a batch of attack vectors (N episodes)."""
        return [self.optimize(a, V_nom, P_nom, verbose=False) for a in attacks]

    def compute_detection_probability(self,
                                        attack: Dict,
                                        V_nom: np.ndarray,
                                        P_nom: np.ndarray) -> Dict:
        """
        Compute probability of detection by each detector type.
        Does NOT run optimization — direct evaluation only.
        """
        pinn_res  = self.pinn.residual(attack["V_spoofed"], attack["P_inj_spoofed"])
        gnn_score = self.gnn.anomaly_score(
            attack["V_spoofed"], attack["P_inj_spoofed"], V_nom, P_nom)
        t_loss    = trust_loss(attack["V_spoofed"], V_nom,
                               attack["P_line_spoofed"], self.P_line_nom(attack["P_line_spoofed"]))

        return {
            "pinn_residual":   pinn_res,
            "gnn_score":       gnn_score,
            "trust_loss":      t_loss,
            "pinn_detected":   pinn_res > 0.05,
            "gnn_detected":    gnn_score > 0.015,
            "trust_detected":  t_loss > 2.0,
            "any_detected":    (pinn_res > 0.05) or (gnn_score > 0.015) or (t_loss > 2.0),
            "pinn_bypass":     pinn_res <= 0.05,
            "gnn_bypass":      gnn_score <= 0.015,
            "fully_stealthy":  (pinn_res <= 0.05) and (gnn_score <= 0.015) and (t_loss <= 2.0),
        }
