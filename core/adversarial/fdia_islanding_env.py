"""
FDIA Islanding RL Environment — PYPY V10.7.

Reinforcement learning environment for stealth FDIA attacks
under partial observability (random 40% sensor dropout).

State space (partial observation):
  - Spoofed voltage measurements (n_buses, partial)
  - Spoofed power injection measurements (n_buses, partial)
  - Cut-line risk scores (n_lines)
  - Step count (normalized)
  - Previous action embedding

Action space:
  - Continuous perturbation vector for up to 5 target lines
  - Strategy selection (one-hot: 5 strategies)

Reward function:
  r = w1 * load_shed_ratio
    + w2 * islanding_bonus
    - w3 * detection_penalty
    + w4 * stealth_score

Episode terminates on:
  - Islanding detected (success)
  - PINN/GNN detection (failure)
  - Max steps reached (neutral)

Compatible with the existing PYPY V10 CascadingFailureSimulator.
"""
import os
import sys
import numpy as np
from typing import Dict, List, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from core.adversarial.cutline_discovery_engine import CutLineDiscoveryEngine
from core.adversarial.zero_parameter_fdia import ZeroParameterFDIA
from core.adversarial.stealth_fdia_optimizer import StealthFDIAOptimizer


# ---------------------------------------------------------------------------
# Environment constants
# ---------------------------------------------------------------------------
MAX_STEPS       = 10
N_TARGET_LINES  = 5          # max lines targeted per step
OBSERVABILITY   = 0.60       # fraction of sensors active (40% dropout)
DETECTION_THRESH_PINN = 0.05
DETECTION_THRESH_GNN  = 0.015

# Reward weights
W_LOAD_SHED    = 2.0
W_ISLANDING    = 5.0
W_DETECTION    = -3.0
W_STEALTH      = 1.0
W_PROGRESS     = 0.5        # shaped reward for cut-line targeting


class FDIAIslandingEnv:
    """
    FDIA Islanding RL Environment.

    Wraps the Zero-Parameter FDIA generator and CascadingFailureSimulator
    to provide a standard gym-like interface for training attack policies.

    Partial Observability: A random 40% of sensors are blinded each episode
    (new dropout mask per reset) — forces policy to be robust to missing data.
    """

    def __init__(self,
                 topo,
                 observability: float = OBSERVABILITY,
                 max_steps: int = MAX_STEPS,
                 n_target_lines: int = N_TARGET_LINES,
                 seed: int = 42,
                 use_cascade_sim: bool = True):
        """
        Args:
            topo:            Grid topology (MultiGridTopology or GridTopology)
            observability:   Fraction of sensors active [0.5, 1.0]
            max_steps:       Max steps per episode
            n_target_lines:  Max lines targeted per step
            seed:            Random seed
            use_cascade_sim: Whether to use CascadingFailureSimulator for reward
        """
        self.topo = topo
        self.observability = observability
        self.max_steps = max_steps
        self.n_target_lines = n_target_lines
        self.rng = np.random.RandomState(seed)
        self.use_cascade_sim = use_cascade_sim

        # Topology dimensions
        self.n_buses = topo.num_buses
        self.n_lines = len(topo.lines)
        self.line_ids = [l["id"] for l in topo.lines]

        # Build components
        self.discovery = CutLineDiscoveryEngine(topo, seed=seed)
        self.fdia      = ZeroParameterFDIA(topo, seed=seed)
        self.optimizer = StealthFDIAOptimizer(topo, seed=seed)

        # Pre-compute risk scores and cut-lines
        self.risk_scores = self.discovery.compute_islanding_risk()
        self.cut_lines   = self.discovery.discover_bridges()
        self.risk_vec    = np.array(
            [self.risk_scores.get(lid, 0.0) for lid in self.line_ids],
            dtype=np.float32
        )

        # Try to load cascade simulator
        self._cascade_sim = None
        if use_cascade_sim:
            try:
                from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator
                self._cascade_sim = CascadingFailureSimulator(topo)
            except Exception:
                self._cascade_sim = None

        # Observation and action dimensions
        # obs: [V_masked (n_buses), P_masked (n_buses), risk_vec (n_lines), step_norm (1)]
        self.obs_dim = self.n_buses + self.n_buses + self.n_lines + 1
        # action: perturbation scale (1), target selection (n_lines), strategy (5)
        self.act_dim = 1 + self.n_lines + 5

        # Episode state
        self.reset()

    # ------------------------------------------------------------------
    # gym-like interface
    # ------------------------------------------------------------------

    def reset(self) -> np.ndarray:
        """Reset environment for new episode. Returns initial observation."""
        self.step_count = 0
        self.done = False
        self.total_load_shed = 0.0
        self.islanding_occurred = False
        self.detected = False

        # New sensor dropout mask for this episode
        n_sensors = self.n_buses + self.n_lines
        mask = self.rng.binomial(1, self.observability, n_sensors).astype(np.float32)
        self.bus_mask  = mask[:self.n_buses]
        self.line_mask = mask[self.n_buses:]

        # Current measurement state (starts at nominal)
        self.V_current  = self.fdia.V_nom.copy()
        self.P_current  = self.fdia.P_nom.copy()

        return self._get_obs()

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one FDIA step.

        Args:
            action: (act_dim,) array:
              [0]:      perturbation scale ∈ [-1, 1]
              [1:n+1]:  line targeting logits (softmax → target selection)
              [n+1:n+6]: strategy logits (argmax → strategy)

        Returns:
            obs:    next observation
            reward: scalar reward
            done:   episode termination flag
            info:   dict with diagnostics
        """
        if self.done:
            return self._get_obs(), 0.0, True, {"error": "episode_already_done"}

        # --- Parse action ---
        action = np.array(action, dtype=np.float32)
        perturb_scale = float(np.clip(action[0], -1.0, 1.0))
        line_logits  = action[1:1 + self.n_lines] if len(action) > 1 + self.n_lines else self.risk_vec
        strat_logits = action[1 + self.n_lines:] if len(action) > 1 + self.n_lines else np.zeros(5)

        # Target lines: weighted by risk + action logits
        effective_logits = self.risk_vec * 0.5 + line_logits[:self.n_lines] * 0.5
        # Softmax sampling for exploration
        probs = self._softmax(effective_logits)
        k = min(self.n_target_lines, self.n_lines)
        target_idx = self.rng.choice(self.n_lines, size=k, replace=False, p=probs)
        target_lines = [self.line_ids[i] for i in target_idx]

        # Strategy selection
        if len(strat_logits) >= 5:
            strategy_idx = int(np.argmax(strat_logits[:5]))
        else:
            strategy_idx = 4  # default: stealthy
        strategies = ["voltage_only", "power_only", "frequency_only", "combined", "stealthy"]
        strategy = strategies[strategy_idx]

        # Scale perturbation bounds by action scale
        scale_factor = max(0.1, (perturb_scale + 1.0) / 2.0)

        # --- Generate FDIA ---
        attack = self.fdia.generate_fdia(
            target_lines=target_lines,
            strategy=strategy,
        )

        # --- Compute detection probability ---
        detection_info = self.optimizer.compute_detection_probability(
            attack, self.fdia.V_nom, self.fdia.P_nom
        )

        # --- Simulate physical impact ---
        load_shed_ratio, islanding, n_islands = self._simulate_impact(target_lines)

        # --- Compute reward ---
        reward = self._compute_reward(
            load_shed_ratio=load_shed_ratio,
            islanding=islanding,
            n_islands=n_islands,
            detection_info=detection_info,
            stealth_score=attack["stealth_score"],
            target_risk=float(np.mean([self.risk_scores.get(lid, 0.0) for lid in target_lines])),
        )

        # --- Update state ---
        self.total_load_shed += load_shed_ratio
        if islanding:
            self.islanding_occurred = True
        if detection_info["any_detected"]:
            self.detected = True

        # Update current measurement estimates
        self.V_current = attack["V_spoofed"].copy()
        self.P_current = attack["P_inj_spoofed"].copy()

        self.step_count += 1

        # --- Termination conditions ---
        terminated = islanding or detection_info["any_detected"]
        truncated  = self.step_count >= self.max_steps
        self.done  = terminated or truncated

        info = {
            "target_lines":      target_lines,
            "strategy":          strategy,
            "load_shed_ratio":   load_shed_ratio,
            "islanding":         islanding,
            "n_islands":         n_islands,
            "pinn_detected":     detection_info["pinn_detected"],
            "gnn_detected":      detection_info["gnn_detected"],
            "any_detected":      detection_info["any_detected"],
            "pinn_residual":     detection_info["pinn_residual"],
            "gnn_score":         detection_info["gnn_score"],
            "stealth_score":     attack["stealth_score"],
            "delta_V_norm":      attack["delta_V_norm"],
            "delta_f":           attack["delta_f"],
            "step":              self.step_count,
        }

        return self._get_obs(), reward, self.done, info

    # ------------------------------------------------------------------
    # Reward
    # ------------------------------------------------------------------

    def _compute_reward(self,
                         load_shed_ratio: float,
                         islanding: bool,
                         n_islands: int,
                         detection_info: Dict,
                         stealth_score: float,
                         target_risk: float) -> float:
        """Multi-objective reward function."""
        r  = W_LOAD_SHED  * load_shed_ratio
        r += W_ISLANDING  * (1.0 if islanding else 0.0)
        r += W_STEALTH    * stealth_score
        r += W_PROGRESS   * target_risk        # shaped reward for targeting risky lines
        r += W_DETECTION  * (1.0 if detection_info["any_detected"] else 0.0)

        # Multi-island bonus: extra reward for fragmenting grid
        if n_islands > 2:
            r += 1.0 * (n_islands - 2)

        return float(r)

    # ------------------------------------------------------------------
    # Physical impact simulation
    # ------------------------------------------------------------------

    def _simulate_impact(self, target_lines: List[str]) -> Tuple[float, bool, int]:
        """
        Simulate the physical impact of tripping target_lines.
        Returns (load_shed_ratio, islanding, n_islands).
        """
        if self._cascade_sim is not None:
            return self._simulate_cascade(target_lines)
        else:
            return self._simulate_heuristic(target_lines)

    def _simulate_cascade(self, target_lines: List[str]) -> Tuple[float, bool, int]:
        """Use CascadingFailureSimulator for accurate physics."""
        try:
            breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
            for lid in target_lines:
                if lid in breakers:
                    breakers[lid] = "OPEN"

            result = self._cascade_sim.simulate(breakers)
            load_shed = result.get("total_load_shed", 0.0)
            total_load = result.get("total_load", 1.0)
            n_islands = result.get("n_islands", 1)
            load_shed_ratio = load_shed / max(total_load, 1e-9)
            islanding = n_islands > 1

            return float(load_shed_ratio), bool(islanding), int(n_islands)
        except Exception:
            return self._simulate_heuristic(target_lines)

    def _simulate_heuristic(self, target_lines: List[str]) -> Tuple[float, bool, int]:
        """
        Heuristic simulation when cascade simulator unavailable.
        Uses bridge count and load split estimation.
        """
        bridges = set(self.discovery.discover_bridges())
        n_bridge_hits = sum(1 for lid in target_lines if lid in bridges)
        risk_mean = float(np.mean([
            self.risk_scores.get(lid, 0.0) for lid in target_lines
        ]))

        # Islanding: occurs if any bridge is targeted
        islanding = n_bridge_hits > 0

        # Load shed: proportional to risk × number of high-risk lines targeted
        base_shed = risk_mean * 0.4 + n_bridge_hits * 0.15
        noise = self.rng.uniform(-0.05, 0.05)
        load_shed_ratio = float(np.clip(base_shed + noise, 0.0, 1.0))

        # Number of islands: 1 + bridge hits (approximate)
        n_islands = 1 + n_bridge_hits

        return load_shed_ratio, islanding, n_islands

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def _get_obs(self) -> np.ndarray:
        """
        Build partial observation vector.
        Masked sensors are replaced with zeros.
        """
        V_obs  = self.V_current  * self.bus_mask   # (n_buses,)
        P_obs  = self.P_current  * self.bus_mask   # (n_buses,)
        risk   = self.risk_vec * self.line_mask    # (n_lines,)
        step_n = np.array([self.step_count / self.max_steps], dtype=np.float32)

        obs = np.concatenate([V_obs, P_obs, risk, step_n])
        return obs.astype(np.float32)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        x = x - x.max()
        ex = np.exp(x)
        return ex / (ex.sum() + 1e-9)

    # ------------------------------------------------------------------
    # Episode statistics
    # ------------------------------------------------------------------

    def episode_summary(self) -> Dict:
        """Return episode summary statistics."""
        return {
            "steps":             self.step_count,
            "total_load_shed":   self.total_load_shed,
            "islanding":         self.islanding_occurred,
            "detected":          self.detected,
            "success":           self.islanding_occurred and not self.detected,
            "n_cut_lines":       len(self.cut_lines),
        }

    # ------------------------------------------------------------------
    # Rollout helper
    # ------------------------------------------------------------------

    def rollout_random_policy(self, n_episodes: int = 100) -> Dict:
        """
        Run N episodes with random policy for baseline measurement.
        """
        results = {
            "load_shed":    [],
            "islanding":    [],
            "detected":     [],
            "success":      [],
            "stealth":      [],
            "rewards":      [],
        }
        for ep in range(n_episodes):
            obs = self.reset()
            ep_reward = 0.0
            while not self.done:
                action = self.rng.randn(self.act_dim).astype(np.float32)
                obs, r, done, info = self.step(action)
                ep_reward += r
            summary = self.episode_summary()
            results["load_shed"].append(summary["total_load_shed"])
            results["islanding"].append(float(summary["islanding"]))
            results["detected"].append(float(summary["detected"]))
            results["success"].append(float(summary["success"]))
            results["rewards"].append(ep_reward)
        return {k: np.array(v) for k, v in results.items()}

    def rollout_greedy_policy(self, n_episodes: int = 100) -> Dict:
        """
        Run N episodes with greedy cut-line targeting policy.
        Always targets top-k highest-risk lines with stealthy strategy.
        """
        top_k = self.discovery.get_top_k_cut_lines(k=self.n_target_lines)
        target_idx = [self.line_ids.index(lid) for lid in top_k if lid in self.line_ids]

        results = {
            "load_shed":    [],
            "islanding":    [],
            "detected":     [],
            "success":      [],
            "stealth":      [],
            "rewards":      [],
        }
        for ep in range(n_episodes):
            obs = self.reset()
            ep_reward = 0.0
            while not self.done:
                # Greedy action: high weight on top-k target lines
                action = np.zeros(self.act_dim, dtype=np.float32)
                action[0] = 0.5  # moderate scale
                for idx in target_idx:
                    if idx < self.n_lines:
                        action[1 + idx] = 2.0  # boost logit
                action[1 + self.n_lines + 4] = 5.0  # force stealthy strategy
                obs, r, done, info = self.step(action)
                ep_reward += r
            summary = self.episode_summary()
            results["load_shed"].append(summary["total_load_shed"])
            results["islanding"].append(float(summary["islanding"]))
            results["detected"].append(float(summary["detected"]))
            results["success"].append(float(summary["success"]))
            results["rewards"].append(ep_reward)
        return {k: np.array(v) for k, v in results.items()}
