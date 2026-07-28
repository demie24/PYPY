"""
MAML Meta-Learner — PYPY V10.6.2.

First-order MAML (FOMAML) for rapid adaptation of the CriticalityAwareEncoder
and PolicyNetwork to unseen grids.

Architecture:
  - Meta-train on: IEEE14, IEEE39, IEEE57 (3 source tasks)
  - Meta-test (adapt) on: IEEE118 (held-out target)
  - Inner loop: K=5 gradient steps per task
  - Outer loop: N_META=200 meta-iterations

FOMAML Algorithm:
  For each meta-iteration:
    1. Sample a task (grid) τ_i
    2. Compute inner-loop adapted policy θ'_i via K gradient steps on τ_i
    3. Compute meta-loss on held-out episodes from τ_i using θ'_i
    4. Update meta-parameters θ via outer gradient from sum of meta-losses

Key insight: MAML finds an initialization θ* that can be quickly adapted to
any new grid with just a few gradient steps. This directly addresses the
zero-shot vs fine-tune gap observed in V10.6.1.

All computation is pure numpy (first-order approximation, no second derivatives).
"""
import os
import sys
import copy
import random
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


class PolicySnapshot:
    """
    Lightweight snapshot of PolicyNetwork weights for MAML inner-loop adaptation.
    Supports copy, step, and restore operations.
    """

    def __init__(self, policy):
        self.W1 = policy.W1.copy()
        self.b1 = policy.b1.copy()
        self.W2 = policy.W2.copy()
        self.b2 = policy.b2.copy()
        self.W3 = policy.W3.copy()
        self.b3 = policy.b3.copy()
        self.lr = float(policy.lr)
        self.latent_dim  = policy.latent_dim
        self.hidden_dim  = policy.hidden_dim
        self.action_dim  = policy.action_dim

    def forward(self, z: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        h1 = np.maximum(z @ self.W1 + self.b1, 0.0)
        h2 = np.maximum(h1 @ self.W2 + self.b2, 0.0)
        logits = h2 @ self.W3 + self.b3
        return logits, h1, h2

    def softmax_masked(self, logits: np.ndarray, n_valid: int) -> np.ndarray:
        masked = logits.copy()
        masked[n_valid:] = -1e9
        masked -= masked.max()
        exp_v = np.exp(masked)
        return exp_v / (exp_v.sum() + 1e-9)

    def sample_action(self, z: np.ndarray, n_valid: int, k: int = 3,
                      temperature: float = 1.0) -> Tuple[np.ndarray, float]:
        logits, _, _ = self.forward(z)
        logits_t = logits / (temperature + 1e-9)
        probs = self.softmax_masked(logits_t, n_valid)
        gumbel = -np.log(-np.log(np.random.random(n_valid) + 1e-9) + 1e-9)
        scores = probs[:n_valid] + gumbel
        targets = np.argsort(scores)[-k:]
        log_prob = np.sum(np.log(probs[targets] + 1e-9))
        return targets, log_prob

    def gradient_step(self, z: np.ndarray, targets: np.ndarray,
                      reward: float, n_valid: int, baseline: float = 0.0,
                      entropy_coef: float = 0.02,
                      inner_lr: float = 1e-3) -> "PolicySnapshot":
        """
        Computes a single REINFORCE gradient step and returns a NEW snapshot.
        Does NOT modify self (for MAML compatibility).
        """
        logits, h1, h2 = self.forward(z)
        probs = self.softmax_masked(logits, n_valid)

        advantage = reward - baseline
        entropy = -np.sum(probs[:n_valid] * np.log(probs[:n_valid] + 1e-9))

        d_probs = probs.copy()
        for t in targets:
            d_probs[t] -= 1.0 / len(targets)
        d_logits = advantage * d_probs - entropy_coef * (-np.log(probs + 1e-9) - 1)
        d_logits[n_valid:] = 0.0

        dW3 = np.outer(h2, d_logits) / len(targets)
        db3 = d_logits
        dh2 = d_logits @ self.W3.T
        dh2[h2 <= 0] = 0.0
        dW2 = np.outer(h1, dh2) / len(targets)
        db2 = dh2
        dh1 = dh2 @ self.W2.T
        dh1[h1 <= 0] = 0.0
        dW1 = np.outer(z, dh1) / len(targets)
        db1 = dh1

        # Create new snapshot with updated weights
        new_snap = PolicySnapshot.__new__(PolicySnapshot)
        clip = 5.0
        new_snap.W1 = self.W1 - inner_lr * np.clip(dW1, -clip, clip)
        new_snap.b1 = self.b1 - inner_lr * np.clip(db1, -clip, clip)
        new_snap.W2 = self.W2 - inner_lr * np.clip(dW2, -clip, clip)
        new_snap.b2 = self.b2 - inner_lr * np.clip(db2, -clip, clip)
        new_snap.W3 = self.W3 - inner_lr * np.clip(dW3, -clip, clip)
        new_snap.b3 = self.b3 - inner_lr * np.clip(db3, -clip, clip)
        new_snap.lr = self.lr
        new_snap.latent_dim = self.latent_dim
        new_snap.hidden_dim = self.hidden_dim
        new_snap.action_dim = self.action_dim
        return new_snap

    def restore_to(self, policy):
        """Copies snapshot weights back into a policy object."""
        policy.W1 = self.W1.copy()
        policy.b1 = self.b1.copy()
        policy.W2 = self.W2.copy()
        policy.b2 = self.b2.copy()
        policy.W3 = self.W3.copy()
        policy.b3 = self.b3.copy()


class MAMLMetaLearner:
    """
    First-Order MAML meta-learner for cross-grid transfer.

    Finds a meta-initialization θ* for the PolicyNetwork such that
    adapting to any new grid requires only K inner-loop gradient steps.

    Usage:
        maml = MAMLMetaLearner(encoder, policy, train_topologies, lr=1e-3)
        maml.meta_train(n_iterations=200, inner_lr=1e-2, inner_steps=5)
        adapted = maml.adapt(target_topo, n_steps=10)  # few-shot adaptation
        z = encoder.encode(target_topo)
        targets, _ = adapted.sample_action(z, len(target_topo.lines), k=3)
    """

    def __init__(self, encoder, policy, train_topologies: List,
                 meta_lr: float = 1e-3, k_targets: int = 3, seed: int = 42):
        """
        Args:
            encoder          : CriticalityAwareEncoder (for encoding grids to z)
            policy           : PolicyNetwork (meta-parameters to optimize)
            train_topologies : Source grids for meta-training (IEEE14, 39, 57)
            meta_lr          : Outer-loop meta learning rate
            k_targets        : Number of concurrent attack targets
            seed             : Random seed
        """
        self.encoder = encoder
        self.policy  = policy
        self.train_topos = train_topologies
        self.meta_lr = meta_lr
        self.k = k_targets

        self.meta_train_rewards: List[float] = []
        self.adaptation_rewards: Dict[str, List[float]] = {}

        np.random.seed(seed)
        random.seed(seed)
        self._seed = seed

    def _simulate_episode(self, topo, snap: PolicySnapshot,
                          noise_std: float = 0.10,
                          temperature: float = 1.0) -> Tuple[np.ndarray, float, np.ndarray]:
        """
        Simulates a single episode on topo using the policy snapshot.
        Returns (z, reward, targets).
        """
        from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator

        z = self.encoder.encode(topo, noise_std=noise_std)
        n_valid = len(topo.lines)
        T = np.clip(temperature + np.random.randn() * 0.3, 0.1, 3.0)
        targets, _ = snap.sample_action(z, n_valid, k=self.k, temperature=T)

        # Translate targets to line IDs
        all_ids = [l["id"] for l in topo.lines]
        tripped = set(all_ids[int(i) % n_valid] for i in targets[:min(self.k, n_valid)])

        sim = CascadingFailureSimulator(topo)
        result = sim.run_cascade(initial_tripped_lines=tripped)

        total_load = sum(l["P_nom"] for l in topo.loads.values()) + 1e-9
        shed = float(result["load_shed"])
        casc = int(result["cascade_size"])
        bo   = 1.0 if shed / total_load >= 0.30 else 0.0
        reward = shed / total_load + 0.1 * casc / max(n_valid, 1) + 2.0 * bo

        return z, reward, targets

    def _inner_loop(self, topo, snap: PolicySnapshot,
                    inner_steps: int = 5,
                    inner_lr: float = 1e-2,
                    n_support: int = 5,
                    noise_std: float = 0.10) -> PolicySnapshot:
        """
        Inner loop: K gradient steps on support set from topo.
        Returns adapted policy snapshot.
        """
        adapted = snap
        baseline = 0.0

        for step in range(inner_steps):
            n_valid = len(topo.lines)
            z, reward, targets = self._simulate_episode(
                topo, adapted, noise_std=noise_std, temperature=1.0 + step * 0.1)
            baseline = 0.9 * baseline + 0.1 * reward
            adapted = adapted.gradient_step(
                z, targets, reward, n_valid,
                baseline=baseline, inner_lr=inner_lr
            )

        return adapted

    def meta_train(self, n_iterations: int = 200,
                   inner_steps: int = 5,
                   inner_lr: float = 1e-2,
                   n_query: int = 5,
                   noise_std: float = 0.10,
                   verbose_every: int = 50) -> List[float]:
        """
        FOMAML outer loop training.

        Each meta-iteration:
          1. For each source task (grid):
             a. Adapt policy via inner_steps on support set
             b. Evaluate on query set using adapted policy
             c. Accumulate outer gradients
          2. Update meta-parameters with accumulated outer gradients

        Returns: List of meta-loss per iteration.
        """
        meta_losses = []

        for it in range(n_iterations):
            it_seed = self._seed * 100000 + it

            # Accumulated outer gradients across tasks
            dW1_meta = np.zeros_like(self.policy.W1)
            db1_meta = np.zeros_like(self.policy.b1)
            dW2_meta = np.zeros_like(self.policy.W2)
            db2_meta = np.zeros_like(self.policy.b2)
            dW3_meta = np.zeros_like(self.policy.W3)
            db3_meta = np.zeros_like(self.policy.b3)

            meta_loss_it = 0.0

            for task_idx, topo in enumerate(self.train_topos):
                np.random.seed(it_seed + task_idx)
                snap = PolicySnapshot(self.policy)

                # Inner loop adaptation (support set)
                adapted = self._inner_loop(
                    topo, snap,
                    inner_steps=inner_steps,
                    inner_lr=inner_lr,
                    noise_std=noise_std
                )

                # Query set evaluation: compute outer gradients
                n_valid = len(topo.lines)
                query_baseline = 0.0
                task_outer_loss = 0.0

                for qi in range(n_query):
                    z, reward, targets = self._simulate_episode(
                        topo, adapted, noise_std=noise_std, temperature=1.0)
                    query_baseline = 0.9 * query_baseline + 0.1 * reward

                    # Compute gradient of query loss w.r.t. ADAPTED parameters
                    logits, h1, h2 = adapted.forward(z)
                    probs = adapted.softmax_masked(logits, n_valid)
                    advantage = reward - query_baseline

                    d_probs = probs.copy()
                    for t in targets:
                        d_probs[t] -= 1.0 / len(targets)
                    d_logits = advantage * d_probs
                    d_logits[n_valid:] = 0.0

                    pg_loss = -np.mean(np.log(probs[targets] + 1e-9)) * advantage
                    task_outer_loss += pg_loss

                    # FOMAML: use adapted gradients as outer gradient approximation
                    clip = 2.0
                    dW3_meta += np.clip(np.outer(h2, d_logits) / len(targets), -clip, clip)
                    db3_meta += np.clip(d_logits, -clip, clip)
                    dh2 = d_logits @ adapted.W3.T
                    dh2[h2 <= 0] = 0.0
                    dW2_meta += np.clip(np.outer(h1, dh2) / len(targets), -clip, clip)
                    db2_meta += np.clip(dh2, -clip, clip)
                    dh1 = dh2 @ adapted.W2.T
                    dh1[h1 <= 0] = 0.0
                    dW1_meta += np.clip(np.outer(z, dh1) / len(targets), -clip, clip)
                    db1_meta += np.clip(dh1, -clip, clip)

                meta_loss_it += task_outer_loss / n_query

            # Outer loop update: scale by 1/n_tasks
            n_tasks = len(self.train_topos)
            clip = 5.0
            self.policy.W3 -= np.clip(self.meta_lr * dW3_meta / n_tasks, -clip, clip)
            self.policy.b3 -= np.clip(self.meta_lr * db3_meta / n_tasks, -clip, clip)
            self.policy.W2 -= np.clip(self.meta_lr * dW2_meta / n_tasks, -clip, clip)
            self.policy.b2 -= np.clip(self.meta_lr * db2_meta / n_tasks, -clip, clip)
            self.policy.W1 -= np.clip(self.meta_lr * dW1_meta / n_tasks, -clip, clip)
            self.policy.b1 -= np.clip(self.meta_lr * db1_meta / n_tasks, -clip, clip)

            meta_loss_it /= n_tasks
            meta_losses.append(meta_loss_it)
            self.meta_train_rewards.append(-meta_loss_it)  # sign flip for reward

            if verbose_every > 0 and (it + 1) % verbose_every == 0:
                print(f"  [MAML] Iter {it+1:4d}/{n_iterations}: "
                      f"meta_loss={meta_loss_it:.4f}")

        return meta_losses

    def adapt(self, target_topo, n_steps: int = 10,
              inner_lr: float = 1e-2, noise_std: float = 0.10) -> PolicySnapshot:
        """
        Few-shot adaptation to a target grid.

        Args:
            target_topo: New/unseen grid topology
            n_steps    : Gradient steps for adaptation (default=10)
            inner_lr   : Adaptation learning rate
            noise_std  : Noise for stochastic evaluation
        Returns:
            Adapted PolicySnapshot ready for evaluation
        """
        snap = PolicySnapshot(self.policy)
        baseline = 0.0

        for step in range(n_steps):
            n_valid = len(target_topo.lines)
            z, reward, targets = self._simulate_episode(
                target_topo, snap, noise_std=noise_std, temperature=1.0)
            baseline = 0.9 * baseline + 0.1 * reward
            snap = snap.gradient_step(
                z, targets, reward, n_valid,
                baseline=baseline, inner_lr=inner_lr
            )

        return snap

    def evaluate_adapted(self, target_topo, n_seeds: int = 10,
                         n_trials: int = 50, noise_std: float = 0.10,
                         adaptation_steps: int = 10) -> Dict[str, Any]:
        """
        Evaluates meta-learned policy on target grid with adaptation.
        Returns statistics for comparison with baseline methods.
        """
        from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator

        seeds = [42 + i * 13 for i in range(n_seeds)]
        sheds, cascs, bos = [], [], []

        for seed in seeds:
            np.random.seed(seed)
            random.seed(seed)
            # Adapt from meta-initialization
            adapted = self.adapt(target_topo, n_steps=adaptation_steps,
                                 noise_std=noise_std)
            n_valid = len(target_topo.lines)
            all_ids = [l["id"] for l in target_topo.lines]

            for trial in range(n_trials):
                trial_seed = seed * 1000 + trial
                np.random.seed(trial_seed)
                z, _, _ = self._simulate_episode(target_topo, adapted, noise_std=noise_std)
                targets, _ = adapted.sample_action(z, n_valid, k=self.k, temperature=1.0)
                tripped = set(all_ids[int(t) % n_valid] for t in targets)

                sim = CascadingFailureSimulator(target_topo)
                res = sim.run_cascade(initial_tripped_lines=tripped)
                total_load = sum(l["P_nom"] for l in target_topo.loads.values()) + 1e-9
                shed = float(res["load_shed"])
                casc = int(res["cascade_size"])
                bo   = 1.0 if shed / total_load >= 0.30 else 0.0
                sheds.append(shed); cascs.append(casc); bos.append(bo)

        return {
            "mean_shed": float(np.mean(sheds)),
            "std_shed":  float(np.std(sheds)),
            "mean_casc": float(np.mean(cascs)),
            "bo_rate":   float(np.mean(bos)),
            "n_samples": len(sheds),
        }


if __name__ == "__main__":
    from core.digital_twin.multi_grid_topology import MultiGridTopology, SUPPORTED_GRIDS
    from core.transfer.criticality_encoder import CriticalityAwareEncoder
    from core.adversarial.transfer_pathogen_agent import PolicyNetwork

    train_grids = ["ieee14", "ieee39", "ieee57"]
    topos_train = [MultiGridTopology(g) for g in train_grids]
    topo_test   = MultiGridTopology("ieee118")

    encoder = CriticalityAwareEncoder(encoder_lr=1e-3)
    policy  = PolicyNetwork(latent_dim=128, seed=42)

    maml = MAMLMetaLearner(encoder, policy, topos_train, meta_lr=1e-3)
    losses = maml.meta_train(n_iterations=50, verbose_every=10)
    print(f"Meta-train done. Final loss: {losses[-1]:.4f}")

    # Adapt to IEEE118
    adapted = maml.adapt(topo_test, n_steps=10)
    print(f"Adapted to IEEE118. Evaluating...")
    metrics = maml.evaluate_adapted(topo_test, n_seeds=3, n_trials=5)
    print(f"Meta-PPO IEEE118: shed={metrics['mean_shed']:.4f}±{metrics['std_shed']:.4f}")
