"""
Domain Randomizer — PYPY V10.6.1 Scientific Enhancement Patch.

Introduces controlled stochasticity into grid topology features during training
to improve zero-shot generalization. Implements:

  1. Line capacity perturbation  (±10%)
  2. Load demand perturbation    (±15%)
  3. Generator output perturbation (±10%)
  4. Topology perturbation (5% probability of temporarily removing a line)

Also provides stochastic latent encoding for evaluation:
  5. Latent perturbation noise   (configurable σ)
  6. Temperature jitter          (randomized sampling temperature)

Inspired by Domain Randomization (Tobin et al., 2017) adapted for power
system transfer learning (Ceesay, 2024).
"""
import os
import sys
import copy
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


# -----------------------------------------------------------------------
# Perturbed Grid Proxy Object
# -----------------------------------------------------------------------
class PerturbedGridProxy:
    """
    A lightweight proxy that wraps a MultiGridTopology and applies
    randomized perturbations to its electrical parameters.

    The proxy exposes the same API as GridTopology/MultiGridTopology:
        .num_buses, .slack_bus, .generators, .loads, .lines, .grid_name
    """

    def __init__(self, base_topo, rng: np.random.RandomState,
                 cap_noise: float = 0.10,
                 load_noise: float = 0.15,
                 gen_noise: float = 0.10,
                 topo_perturb_prob: float = 0.05):
        """
        Args:
            base_topo:  Original MultiGridTopology (read-only)
            rng:        Seeded numpy RandomState for reproducibility
            cap_noise:  Line reactance perturbation σ (±fraction)
            load_noise: Load demand perturbation σ
            gen_noise:  Generator output perturbation σ
            topo_perturb_prob: Probability of dropping a non-critical line
        """
        self.grid_name = getattr(base_topo, "grid_name", "unknown")
        self.slack_bus  = base_topo.slack_bus
        self.num_buses  = base_topo.num_buses
        self._rng = rng

        # Deep-copy and perturb generators
        self.generators = {}
        for bus, g in base_topo.generators.items():
            factor = 1.0 + rng.uniform(-gen_noise, gen_noise)
            self.generators[bus] = {
                **g,
                "P_nom": max(g["P_nom"] * factor, 1e-3),
                "Q_nom": max(g.get("Q_nom", 0.0) * factor, 0.0),
            }

        # Deep-copy and perturb loads
        self.loads = {}
        for bus, l in base_topo.loads.items():
            factor = 1.0 + rng.uniform(-load_noise, load_noise)
            self.loads[bus] = {
                **l,
                "P_nom": max(l["P_nom"] * factor, 1e-4),
                "Q_nom": max(l.get("Q_nom", 0.0) * factor, 0.0),
            }

        # Deep-copy and perturb lines; optionally drop some
        perturbed_lines = []
        for line in base_topo.lines:
            # Skip topology perturbation for transformers (critical)
            is_trafo = "trafo" in line["id"]
            if not is_trafo and rng.random() < topo_perturb_prob:
                continue  # randomly drop this line

            x_factor = 1.0 + rng.uniform(-cap_noise, cap_noise)
            new_line = {
                **line,
                "X": max(line["X"] * x_factor, 1e-4),
                "R": max(line.get("R", 0.0), 0.0),
            }
            perturbed_lines.append(new_line)

        self.lines = perturbed_lines
        self.num_lines = len(self.lines)


# -----------------------------------------------------------------------
# Domain Randomizer
# -----------------------------------------------------------------------
class DomainRandomizer:
    """
    Applies domain randomization to a grid topology for training robustness.

    Usage:
        dr = DomainRandomizer()
        perturbed_topo = dr.randomize(base_topo, seed=42)
        # perturbed_topo has same API as base_topo but with noisy params
    """

    def __init__(self,
                 cap_noise: float = 0.10,
                 load_noise: float = 0.15,
                 gen_noise: float = 0.10,
                 topo_perturb_prob: float = 0.05):
        self.cap_noise = cap_noise
        self.load_noise = load_noise
        self.gen_noise = gen_noise
        self.topo_perturb_prob = topo_perturb_prob

    def randomize(self, base_topo, seed: Optional[int] = None) -> PerturbedGridProxy:
        """
        Returns a perturbed copy of the grid topology.

        Args:
            base_topo: Original grid topology
            seed: Random seed (None = use global np.random state)
        Returns:
            PerturbedGridProxy with same API as base_topo
        """
        rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState(
            np.random.randint(0, 2**31)
        )
        return PerturbedGridProxy(
            base_topo, rng,
            cap_noise=self.cap_noise,
            load_noise=self.load_noise,
            gen_noise=self.gen_noise,
            topo_perturb_prob=self.topo_perturb_prob,
        )

    def randomize_batch(self, base_topo, n: int,
                        base_seed: int = 42) -> List[PerturbedGridProxy]:
        """
        Returns n independently perturbed variants of base_topo.
        Each variant uses seed = base_seed + i for reproducibility.
        """
        return [self.randomize(base_topo, seed=base_seed + i) for i in range(n)]


# -----------------------------------------------------------------------
# Stochastic Encoder Wrapper
# -----------------------------------------------------------------------
class StochasticEncoder:
    """
    Wraps UnifiedGridEncoder with controllable stochastic perturbation
    of the latent vector. Enables different seeds to produce distinct
    attack distributions from the same topology, enabling meaningful
    statistical testing across seeds.

    Perturbation: z_noisy = z + N(0, σ²I)
    This simulates measurement uncertainty and grid state variability.
    """

    def __init__(self, base_encoder, latent_noise_std: float = 0.05):
        """
        Args:
            base_encoder: UnifiedGridEncoder instance
            latent_noise_std: Standard deviation of Gaussian noise added to z
        """
        self.encoder = base_encoder
        self.latent_noise_std = latent_noise_std

    def encode(self, topo, noise: bool = True) -> np.ndarray:
        """
        Encodes a topology to a (possibly noisy) latent vector z.

        Args:
            topo: Grid topology
            noise: If True, add Gaussian perturbation to z
        Returns:
            z: np.ndarray shape (128,), L2-normalized
        """
        z = self.encoder.encode(topo)
        if noise and self.latent_noise_std > 0:
            perturbation = np.random.randn(*z.shape).astype(np.float32)
            z = z + self.latent_noise_std * perturbation
            # Re-normalize
            norm = np.linalg.norm(z) + 1e-9
            z = z / norm
        return z

    def encode_deterministic(self, topo) -> np.ndarray:
        """Deterministic encoding (no noise)."""
        return self.encoder.encode(topo)


# -----------------------------------------------------------------------
# Temperature Scheduler
# -----------------------------------------------------------------------
class TemperatureScheduler:
    """
    Provides temperature schedules for stochastic action sampling.

    Modes:
      - 'fixed':    Always return a constant temperature
      - 'anneal':   Decrease from T_max to T_min over n_steps
      - 'jitter':   Fixed temperature with random jitter ± jitter_std
    """

    def __init__(self, mode: str = "jitter",
                 T_base: float = 1.0,
                 T_min: float = 0.3,
                 T_max: float = 2.0,
                 jitter_std: float = 0.3,
                 n_steps: int = 1000):
        self.mode = mode
        self.T_base = T_base
        self.T_min = T_min
        self.T_max = T_max
        self.jitter_std = jitter_std
        self.n_steps = n_steps
        self._step = 0

    def get(self) -> float:
        """Returns the current temperature."""
        if self.mode == "fixed":
            return self.T_base
        elif self.mode == "anneal":
            progress = min(self._step / max(self.n_steps, 1), 1.0)
            T = self.T_max * (1 - progress) + self.T_min * progress
            self._step += 1
            return float(T)
        elif self.mode == "jitter":
            jitter = np.random.randn() * self.jitter_std
            T = np.clip(self.T_base + jitter, self.T_min, self.T_max)
            self._step += 1
            return float(T)
        else:
            return self.T_base

    def reset(self):
        self._step = 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, project_root)
    from core.digital_twin.multi_grid_topology import MultiGridTopology
    from core.transfer.unified_grid_encoder import UnifiedGridEncoder

    topo = MultiGridTopology("ieee39")
    dr = DomainRandomizer()
    perturbed = dr.randomize(topo, seed=42)
    print(f"Original: {topo.num_lines} lines, {len(topo.loads)} loads")
    print(f"Perturbed: {perturbed.num_lines} lines, {len(perturbed.loads)} loads")

    encoder = UnifiedGridEncoder()
    stoch_enc = StochasticEncoder(encoder, latent_noise_std=0.05)
    z1 = stoch_enc.encode(topo, noise=True)
    z2 = stoch_enc.encode(topo, noise=True)
    print(f"Noisy z1 norm: {np.linalg.norm(z1):.4f}")
    print(f"||z1 - z2||:   {np.linalg.norm(z1 - z2):.6f}  (should be > 0)")
