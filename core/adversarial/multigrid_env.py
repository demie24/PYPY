"""
Multi-Grid Training Environment — PYPY V10.6 Cross-Grid Transfer Learning.

Provides a unified training environment that randomly selects from multiple
IEEE grid topologies, supports curriculum learning (staged grid introduction),
and manages grid-specific cascade simulators.

Curriculum Learning Stages:
    Stage 1 (easiest): IEEE 14-Bus only
    Stage 2:           IEEE 14-Bus + IEEE 39-Bus
    Stage 3:           IEEE 14-Bus + IEEE 39-Bus + IEEE 57-Bus
    Stage 4 (hardest): IEEE 14-Bus + IEEE 39-Bus + IEEE 57-Bus + IEEE 118-Bus
"""
import os
import sys
import random
import numpy as np
from typing import List, Optional, Dict, Any, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.insert(0, project_root)

from core.digital_twin.multi_grid_topology import MultiGridTopology

# Curriculum stages: each stage adds the next grid
CURRICULUM_STAGES = {
    1: ["ieee14"],
    2: ["ieee14", "ieee39"],
    3: ["ieee14", "ieee39", "ieee57"],
    4: ["ieee14", "ieee39", "ieee57", "ieee118"],
}

# Grid display labels
GRID_LABELS = {
    "ieee14": "IEEE 14-Bus",
    "ieee39": "IEEE 39-Bus",
    "ieee57": "IEEE 57-Bus",
    "ieee118": "IEEE 118-Bus",
}


class MultiGridEnv:
    """
    Multi-grid training environment supporting curriculum learning.

    Usage:
        env = MultiGridEnv(curriculum_stage=2)
        topo = env.reset()       # returns a random grid topology
        result = env.step(k=3)   # execute random attack, return metrics
        env.advance_curriculum() # move to next harder stage
    """

    def __init__(self, curriculum_stage: int = 4, seed: int = 42):
        """
        Args:
            curriculum_stage: Initial curriculum stage (1-4)
            seed: Random seed for grid selection
        """
        if curriculum_stage not in CURRICULUM_STAGES:
            raise ValueError(f"Invalid curriculum_stage {curriculum_stage}. Use 1-4.")

        self.curriculum_stage = curriculum_stage
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

        # Pre-load all grids to avoid repeated initialization
        print("[MultiGridEnv] Pre-loading all grid topologies...")
        self._topologies: Dict[str, MultiGridTopology] = {}
        for grid_name in ["ieee14", "ieee39", "ieee57", "ieee118"]:
            try:
                self._topologies[grid_name] = MultiGridTopology(grid_name)
                s = self._topologies[grid_name].get_summary()
                print(f"  Loaded {GRID_LABELS[grid_name]}: "
                      f"{s['num_buses']} buses, {s['num_lines']} lines")
            except Exception as e:
                print(f"  WARNING: Failed to load {grid_name}: {e}")

        self.current_topo: Optional[MultiGridTopology] = None
        self.current_grid_name: str = ""
        self.episode_count: int = 0
        self.stage_history: List[Dict] = []

    def _active_grids(self) -> List[str]:
        """Returns the list of active grids for the current curriculum stage."""
        stage_grids = CURRICULUM_STAGES[self.curriculum_stage]
        return [g for g in stage_grids if g in self._topologies]

    def reset(self, grid_name: Optional[str] = None,
              curriculum_stage: Optional[int] = None) -> MultiGridTopology:
        """
        Resets the environment by selecting a new grid.

        Args:
            grid_name: Optionally force a specific grid (e.g., "ieee39")
            curriculum_stage: Optionally override curriculum stage for this reset
        Returns:
            The selected grid topology
        """
        if curriculum_stage is not None:
            self.curriculum_stage = max(1, min(4, curriculum_stage))

        if grid_name is not None:
            self.current_grid_name = grid_name
        else:
            active = self._active_grids()
            if not active:
                raise RuntimeError("No active grids available for current curriculum stage.")
            self.current_grid_name = random.choice(active)

        self.current_topo = self._topologies[self.current_grid_name]
        self.episode_count += 1
        return self.current_topo

    def step(self, target_indices: np.ndarray, k: int = 3) -> Dict[str, Any]:
        """
        Executes an attack step on the current active grid.

        Args:
            target_indices: Array of line indices to trip (from policy output)
            k: Number of concurrent targets
        Returns:
            Dict with reward, load_shed, cascade_size, blackout, grid info
        """
        if self.current_topo is None:
            raise RuntimeError("Call reset() before step().")

        from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator

        all_line_ids = [l["id"] for l in self.current_topo.lines]
        n_valid = len(all_line_ids)
        k_actual = min(k, n_valid)
        target_indices_clamped = np.clip(target_indices[:k_actual], 0, n_valid - 1)
        tripped = set(all_line_ids[int(i)] for i in target_indices_clamped)

        sim = CascadingFailureSimulator(self.current_topo)
        result = sim.run_cascade(initial_tripped_lines=tripped)

        total_load = sum(l["P_nom"] for l in self.current_topo.loads.values())
        load_shed = float(result["load_shed"])
        cascade_size = int(result["cascade_size"])
        blackout = 1.0 if load_shed / (total_load + 1e-9) >= 0.30 else 0.0

        # Composite reward
        reward = (load_shed / (total_load + 1e-9) +
                  0.1 * cascade_size / max(n_valid, 1) +
                  2.0 * blackout)

        episode_metrics = {
            "grid": self.current_grid_name,
            "grid_label": GRID_LABELS.get(self.current_grid_name, self.current_grid_name),
            "curriculum_stage": self.curriculum_stage,
            "load_shed": load_shed,
            "cascade_size": cascade_size,
            "blackout": blackout,
            "reward": reward,
            "total_load": total_load,
            "n_lines": n_valid,
        }

        self.stage_history.append(episode_metrics)
        return episode_metrics

    def advance_curriculum(self) -> int:
        """
        Advances to the next curriculum stage (harder grid set).
        Returns the new curriculum stage.
        """
        if self.curriculum_stage < 4:
            self.curriculum_stage += 1
            print(f"[MultiGridEnv] Curriculum advanced to Stage {self.curriculum_stage}: "
                  f"{CURRICULUM_STAGES[self.curriculum_stage]}")
        return self.curriculum_stage

    def run_curriculum_training(self, agent, episodes_per_stage: int = 100,
                                k: int = 3, verbose: bool = True) -> Dict[str, List[float]]:
        """
        Runs a full curriculum training loop across all 4 stages.

        Args:
            agent: TransferPatogenAgent instance
            episodes_per_stage: Number of training episodes per curriculum stage
            k: Number of concurrent attack targets
            verbose: Print stage summaries
        Returns:
            Dict {stage_label: list of rewards}
        """
        all_rewards = {}

        for stage in range(1, 5):
            self.curriculum_stage = stage
            active = self._active_grids()
            stage_label = f"Stage{stage}_{'+'.join(active)}"
            stage_rewards = []

            if verbose:
                print(f"\n[Curriculum Stage {stage}] Active grids: {active}")

            for ep in range(episodes_per_stage):
                topo = self.reset(curriculum_stage=stage)
                rewards_ep = agent.train(topo, episodes=1, k=k, verbose=False,
                                        grid_label=stage_label)
                stage_rewards.extend(rewards_ep)

            all_rewards[stage_label] = stage_rewards

            if verbose:
                print(f"  Stage {stage} complete: "
                      f"mean_reward={np.mean(stage_rewards):.4f}, "
                      f"final_reward={stage_rewards[-1]:.4f}")

        return all_rewards

    def get_stage_stats(self) -> Dict[str, Any]:
        """Returns statistics about the current training history."""
        if not self.stage_history:
            return {}

        by_grid = {}
        for rec in self.stage_history:
            g = rec["grid"]
            if g not in by_grid:
                by_grid[g] = {"rewards": [], "load_sheds": [], "blackouts": []}
            by_grid[g]["rewards"].append(rec["reward"])
            by_grid[g]["load_sheds"].append(rec["load_shed"])
            by_grid[g]["blackouts"].append(rec["blackout"])

        stats = {}
        for g, data in by_grid.items():
            stats[g] = {
                "n_episodes": len(data["rewards"]),
                "mean_reward": float(np.mean(data["rewards"])),
                "mean_load_shed": float(np.mean(data["load_sheds"])),
                "blackout_rate": float(np.mean(data["blackouts"])),
            }
        return stats


if __name__ == "__main__":
    env = MultiGridEnv(curriculum_stage=1)
    topo = env.reset()
    print(f"Selected grid: {topo.grid_name}")
    print(f"Active grids: {env._active_grids()}")
