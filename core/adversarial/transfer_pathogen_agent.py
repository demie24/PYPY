"""
Transfer Pathogen Agent — PYPY V10.6 Cross-Grid Transfer Learning.

A cross-topology adversarial attack agent that:
  1. Encodes any IEEE grid into a fixed 128-dim latent vector (UnifiedGridEncoder).
  2. Uses a learned PPO-style policy over a zero-padded 118-dim attack space.
  3. Supports training on IEEE39, fine-tuning on any target grid, and
     zero-shot generalization to unseen grids.

Zero-Padded Attack Representation (Inspired by Ceesay, 2024):
  The attack output is always a 118-dimensional vector (max lines in IEEE118).
  For grids with fewer lines, the valid action space occupies positions [0, n_lines-1]
  and the rest are masked to -inf before softmax sampling. This allows a single
  policy to operate across all grid sizes without architectural changes.

Training Mode:
  Uses REINFORCE (Monte Carlo Policy Gradient) with entropy bonus for exploration.
  Episodes are simulated using the CascadingFailureSimulator on each grid.
"""
import os
import sys
import numpy as np
import random
from typing import List, Dict, Any, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.insert(0, project_root)

from core.transfer.unified_grid_encoder import UnifiedGridEncoder
from core.transfer.domain_adapter import DomainAdapter

# Maximum lines across all supported grids (IEEE 118)
MAX_ACTION_DIM = 186


class PolicyNetwork:
    """
    Lightweight MLP policy: z(128) → logits(MAX_ACTION_DIM).
    Weights stored as numpy arrays; gradients computed manually.
    """

    def __init__(self, latent_dim: int = 128, hidden_dim: int = 256,
                 action_dim: int = MAX_ACTION_DIM, seed: int = 42):
        rng = np.random.RandomState(seed)
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.action_dim = action_dim

        # Layer 1: latent → hidden
        scale1 = np.sqrt(2.0 / latent_dim)
        self.W1 = rng.randn(latent_dim, hidden_dim) * scale1
        self.b1 = np.zeros(hidden_dim)

        # Layer 2: hidden → hidden
        scale2 = np.sqrt(2.0 / hidden_dim)
        self.W2 = rng.randn(hidden_dim, hidden_dim) * scale2
        self.b2 = np.zeros(hidden_dim)

        # Output: hidden → action_dim
        scale3 = np.sqrt(2.0 / hidden_dim)
        self.W3 = rng.randn(hidden_dim, action_dim) * scale3
        self.b3 = np.zeros(action_dim)

        # Learning rate
        self.lr = 3e-4

    def forward(self, z: np.ndarray) -> np.ndarray:
        """
        Forward pass: z (128,) → logits (action_dim,).
        """
        h1 = np.maximum(z @ self.W1 + self.b1, 0)   # ReLU
        h2 = np.maximum(h1 @ self.W2 + self.b2, 0)  # ReLU
        logits = h2 @ self.W3 + self.b3
        return logits, h1, h2

    def softmax_masked(self, logits: np.ndarray, n_valid: int) -> np.ndarray:
        """
        Applies mask for lines [n_valid:] and returns softmax probabilities.
        """
        masked = logits.copy()
        masked[n_valid:] = -1e9  # mask out invalid actions
        # Numerically stable softmax
        masked -= masked.max()
        exp_v = np.exp(masked)
        return exp_v / (exp_v.sum() + 1e-9)

    def sample_action(self, z: np.ndarray, n_valid: int, k: int = 3,
                      temperature: float = 1.0) -> Tuple[np.ndarray, float]:
        """
        Samples K attack targets (without replacement) from the policy distribution.

        Args:
            z: Latent grid embedding (128,)
            n_valid: Number of valid action indices (= num_lines in current grid)
            k: Number of concurrent attack targets
            temperature: Sampling temperature (higher = more random)
        Returns:
            targets: np.ndarray of k action indices
            log_prob: Log probability of the sampled set
        """
        logits, _, _ = self.forward(z)
        logits_t = logits / (temperature + 1e-9)
        probs = self.softmax_masked(logits_t, n_valid)

        # Sample without replacement using Gumbel-max trick
        gumbel = -np.log(-np.log(np.random.random(n_valid) + 1e-9) + 1e-9)
        scores = probs[:n_valid] + gumbel
        targets = np.argsort(scores)[-k:]  # top-k indices

        log_prob = np.sum(np.log(probs[targets] + 1e-9))
        return targets, log_prob

    def update(self, z: np.ndarray, targets: np.ndarray,
               reward: float, n_valid: int, baseline: float = 0.0,
               entropy_coef: float = 0.01):
        """
        REINFORCE policy gradient update with baseline and entropy bonus.
        """
        logits, h1, h2 = self.forward(z)
        probs = self.softmax_masked(logits, n_valid)

        advantage = reward - baseline
        entropy = -np.sum(probs[:n_valid] * np.log(probs[:n_valid] + 1e-9))

        # Policy gradient loss (negative for gradient ascent)
        log_probs_targets = np.log(probs[targets] + 1e-9)
        pg_loss = -np.mean(log_probs_targets) * advantage - entropy_coef * entropy

        # Backprop (manual, simplified chain rule)
        # dL/d_logits
        d_probs = probs.copy()
        for t in targets:
            d_probs[t] -= 1.0 / len(targets)
        d_logits = advantage * d_probs - entropy_coef * (-np.log(probs + 1e-9) - 1)
        d_logits[n_valid:] = 0.0  # zero gradient for masked actions

        # Layer 3 gradient
        dW3 = np.outer(h2, d_logits) * (1.0 / len(targets))
        db3 = d_logits

        # Layer 2 gradient
        dh2 = d_logits @ self.W3.T
        dh2[h2 <= 0] = 0  # ReLU mask
        dW2 = np.outer(h1, dh2) * (1.0 / len(targets))
        db2 = dh2

        # Layer 1 gradient
        dh1 = dh2 @ self.W2.T
        dh1[h1 <= 0] = 0  # ReLU mask
        dW1 = np.outer(z, dh1) * (1.0 / len(targets))
        db1 = dh1

        # Gradient descent (clip for stability)
        clip = 5.0
        self.W3 -= np.clip(self.lr * dW3, -clip, clip)
        self.b3 -= np.clip(self.lr * db3, -clip, clip)
        self.W2 -= np.clip(self.lr * dW2, -clip, clip)
        self.b2 -= np.clip(self.lr * db2, -clip, clip)
        self.W1 -= np.clip(self.lr * dW1, -clip, clip)
        self.b1 -= np.clip(self.lr * db1, -clip, clip)

        return float(pg_loss)


class TransferPatogenAgent:
    """
    Cross-grid transfer learning pathogen agent.

    Capabilities:
      - train(topo, episodes): Train from scratch on a given grid topology
      - finetune(topo, episodes): Fine-tune pre-trained weights on a new grid
      - zero_shot_attack(topo, k): Execute attack on unseen grid without retraining
      - evaluate(topo, seeds, k): Multi-seed evaluation returning metrics
    """

    def __init__(self, num_targets: int = 3, seed: int = 42):
        self.encoder = UnifiedGridEncoder()
        self.adapter = DomainAdapter()
        self.policy = PolicyNetwork(seed=seed)
        self.num_targets = num_targets
        self.seed = seed
        self.training_history: Dict[str, List[float]] = {}
        self._reward_baseline = 0.0

    # ------------------------------------------------------------------
    # Internal: compute reward for a set of line targets
    # ------------------------------------------------------------------
    def _simulate_attack(self, topo, target_indices: np.ndarray) -> Dict[str, float]:
        """
        Translates action indices → line IDs and simulates cascade.
        Returns reward metrics.
        """
        from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator

        # Map action indices to line IDs
        all_line_ids = [l["id"] for l in topo.lines]
        n_valid = len(all_line_ids)
        target_indices_clamped = np.clip(target_indices, 0, n_valid - 1)
        tripped = set(all_line_ids[int(i)] for i in target_indices_clamped)

        # Simulate cascade
        sim = CascadingFailureSimulator(topo)
        result = sim.run_cascade(initial_tripped_lines=tripped)

        total_load = sum(l["P_nom"] for l in topo.loads.values())
        load_shed = float(result["load_shed"])
        cascade_size = int(result["cascade_size"])
        blackout = 1.0 if load_shed / (total_load + 1e-9) >= 0.30 else 0.0

        # Reward: normalized load shed + cascade bonus + blackout bonus
        reward = (load_shed / (total_load + 1e-9) +
                  0.1 * cascade_size / max(n_valid, 1) +
                  2.0 * blackout)

        return {
            "reward": reward,
            "load_shed": load_shed,
            "cascade_size": cascade_size,
            "blackout": blackout,
            "tripped_lines": list(tripped),
        }

    def _get_latent(self, topo) -> np.ndarray:
        """Encodes topo to 128-dim latent vector."""
        return self.encoder.encode(topo)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(self, topo, episodes: int = 200, k: Optional[int] = None,
              verbose: bool = False, grid_label: str = "train") -> List[float]:
        """
        Trains the policy on a single grid from scratch.

        Args:
            topo: Grid topology (MultiGridTopology or GridTopology)
            episodes: Number of training episodes
            k: Number of concurrent attack targets
            verbose: Print progress
            grid_label: Label for logging
        Returns:
            episode_rewards: List of rewards per episode
        """
        k = k or self.num_targets
        n_valid = len(topo.lines)
        z = self._get_latent(topo)

        episode_rewards = []
        self._reward_baseline = 0.0

        for ep in range(episodes):
            targets, log_prob = self.policy.sample_action(z, n_valid, k=k)
            result = self._simulate_attack(topo, targets)
            reward = result["reward"]

            # Update baseline (exponential moving average)
            self._reward_baseline = 0.95 * self._reward_baseline + 0.05 * reward

            # Policy update
            self.policy.update(z, targets, reward, n_valid,
                               baseline=self._reward_baseline)
            episode_rewards.append(reward)

            if verbose and (ep + 1) % 50 == 0:
                print(f"  [{grid_label}] Ep {ep+1}/{episodes}: "
                      f"reward={reward:.4f}, load_shed={result['load_shed']:.3f}")

        self.training_history[grid_label] = episode_rewards
        return episode_rewards

    def finetune(self, topo, episodes: int = 50, k: Optional[int] = None,
                 verbose: bool = False) -> List[float]:
        """
        Fine-tunes the pre-trained policy on a new target grid.
        Uses a reduced learning rate for stable transfer.
        """
        k = k or self.num_targets
        # Reduce learning rate for fine-tuning
        orig_lr = self.policy.lr
        self.policy.lr = orig_lr * 0.1

        label = f"finetune_{getattr(topo, 'grid_name', 'grid')}"
        result = self.train(topo, episodes=episodes, k=k, verbose=verbose,
                            grid_label=label)

        self.policy.lr = orig_lr  # restore
        return result

    # ------------------------------------------------------------------
    # Zero-Shot Evaluation
    # ------------------------------------------------------------------
    def zero_shot_attack(self, topo, k: Optional[int] = None,
                         temperature: float = 0.5) -> Dict[str, Any]:
        """
        Executes a zero-shot attack on an unseen grid topology.
        No retraining is performed — uses pre-trained weights directly.

        Args:
            topo: Target grid topology
            k: Number of concurrent attack targets
            temperature: Sampling temperature (lower = more greedy)
        Returns:
            Dict with attack results
        """
        k = k or self.num_targets
        n_valid = len(topo.lines)
        z = self._get_latent(topo)

        targets, log_prob = self.policy.sample_action(z, n_valid, k=k,
                                                      temperature=temperature)
        result = self._simulate_attack(topo, targets)
        result["target_indices"] = targets.tolist()
        result["log_prob"] = float(log_prob)
        result["grid"] = getattr(topo, "grid_name", "unknown")
        return result

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(self, topo, seeds: List[int], k: Optional[int] = None,
                 n_trials: int = 10, temperature: float = 0.5) -> Dict[str, Any]:
        """
        Multi-seed evaluation of the agent on a given grid.

        Returns:
            Dict with mean/std of load_shed, cascade_size, blackout_rate
        """
        k = k or self.num_targets
        all_sheds, all_cascades, all_bos = [], [], []

        for s in seeds:
            np.random.seed(s)
            random.seed(s)
            for _ in range(n_trials):
                result = self.zero_shot_attack(topo, k=k, temperature=temperature)
                all_sheds.append(result["load_shed"])
                all_cascades.append(result["cascade_size"])
                all_bos.append(result["blackout"])

        return {
            "grid": getattr(topo, "grid_name", "unknown"),
            "mean_load_shed": float(np.mean(all_sheds)),
            "std_load_shed": float(np.std(all_sheds)),
            "mean_cascade": float(np.mean(all_cascades)),
            "std_cascade": float(np.std(all_cascades)),
            "blackout_rate": float(np.mean(all_bos)),
            "n_samples": len(all_sheds),
        }

    # ------------------------------------------------------------------
    # Domain Alignment
    # ------------------------------------------------------------------
    def domain_alignment(self, topo_source, topo_target,
                         method: str = "mmd") -> float:
        """
        Measures the latent space domain gap between two grid topologies.
        """
        z_s = self._get_latent(topo_source).reshape(1, -1)
        z_t = self._get_latent(topo_target).reshape(1, -1)
        return self.adapter.align(z_s, z_t, method=method)

    # ------------------------------------------------------------------
    # Save / Load weights
    # ------------------------------------------------------------------
    def save_weights(self, path: str):
        """Saves policy weights to a .npz file."""
        np.savez(path,
                 W1=self.policy.W1, b1=self.policy.b1,
                 W2=self.policy.W2, b2=self.policy.b2,
                 W3=self.policy.W3, b3=self.policy.b3)
        print(f"[TransferPatogenAgent] Weights saved to {path}")

    def load_weights(self, path: str):
        """Loads policy weights from a .npz file."""
        data = np.load(path)
        self.policy.W1 = data["W1"]
        self.policy.b1 = data["b1"]
        self.policy.W2 = data["W2"]
        self.policy.b2 = data["b2"]
        self.policy.W3 = data["W3"]
        self.policy.b3 = data["b3"]
        print(f"[TransferPatogenAgent] Weights loaded from {path}")


if __name__ == "__main__":
    from core.digital_twin.multi_grid_topology import MultiGridTopology

    agent = TransferPatogenAgent(num_targets=3)

    # Train on IEEE 39
    print("Training on IEEE39...")
    topo39 = MultiGridTopology("ieee39")
    rewards = agent.train(topo39, episodes=20, verbose=True, grid_label="ieee39")
    print(f"Final reward: {rewards[-1]:.4f}")

    # Zero-shot on IEEE57
    print("\nZero-shot evaluation on IEEE57...")
    topo57 = MultiGridTopology("ieee57")
    result = agent.zero_shot_attack(topo57, k=3)
    print(f"Load shed: {result['load_shed']:.4f} pu, Cascade: {result['cascade_size']}")
