"""Reproducible multi-seed evaluation of selected pathogen/immune policies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from core.adversarial.coevolution_env import CoevolutionEnv
from core.adversarial.immune_agent import ImmuneAgent
from core.adversarial.immune_memory import ImmuneMemory
from core.adversarial.pathogen_agent import PathogenAgent


ATTACK_NAMES = ("NO_ACTION", "FDIA", "REPLAY", "DOS", "TRIP_LINE")
DEFENCE_NAMES = ("NO_ACTION", "ISSUE_WARNING", "QUARANTINE_TELEMETRY", "ISOLATE_BUS", "RECONNECT_LINE", "REROUTE_POWER", "RESET_TRUST")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def evaluate_seed(seed: int, episodes: int, red: PathogenAgent, blue: ImmuneAgent, memory_path: Path) -> tuple[dict, list[dict]]:
    seed_everything(seed)
    env = CoevolutionEnv()
    # Evaluation must neither consume nor mutate the repository's historical
    # immune memory. Each seed gets an isolated, initially empty memory store.
    env.immune_memory = ImmuneMemory(persistence_file=str(memory_path))
    env.immune_memory.memory_keys.clear()
    env.immune_memory.memory_values.clear()
    rows = []
    attack_counts: Counter[str] = Counter()
    defence_counts: Counter[str] = Counter()
    nonfinite_observations = 0
    nonfinite_metrics = 0
    for episode in range(episodes):
        episode_seed = seed * 10_000 + episode
        seed_everything(episode_seed)
        observations, info = env.reset(seed=episode_seed)
        totals = {"red": 0.0, "blue": 0.0}
        detected = False
        blackout = False
        load_served = 1.0
        steps = 0
        done = False
        while not done:
            red_state = np.asarray(observations["red"], dtype=np.float32)
            blue_state = np.asarray(observations["blue"], dtype=np.float32)
            nonfinite_observations += int(np.count_nonzero(~np.isfinite(red_state)))
            nonfinite_observations += int(np.count_nonzero(~np.isfinite(blue_state)))
            # A solver failure is an environment outcome, not permission to
            # feed NaN/Inf into a categorical policy. Use an explicit bounded
            # failure representation and retain the count in the artefact.
            red_state = np.nan_to_num(red_state, nan=0.0, posinf=10.0, neginf=-10.0)
            blue_state = np.nan_to_num(blue_state, nan=0.0, posinf=10.0, neginf=-10.0)
            red_action, _, _ = red.select_action(red_state, evaluation=False)
            recalled = info.get("recalled_action")
            blue_action = recalled if recalled is not None else blue.select_action(blue_state, evaluation=False)[0]
            attack_counts[ATTACK_NAMES[int(red_action["type"])]] += 1
            defence_counts[DEFENCE_NAMES[int(blue_action["type"])]] += 1
            observations, rewards, terminated, truncated, info = env.step({"red": red_action, "blue": blue_action})
            for side in ("red", "blue"):
                reward = float(rewards[side])
                if not np.isfinite(reward):
                    nonfinite_metrics += 1
                    reward = 0.0
                totals[side] += reward
            detected |= info.get("global_decision") in ("ATTACK_CONFIRMED", "ISOLATE_COMPONENT")
            blackout |= bool(info.get("blackout", False))
            candidate_load_served = float(info.get("load_served_pct", load_served))
            if np.isfinite(candidate_load_served):
                load_served = candidate_load_served
            else:
                nonfinite_metrics += 1
                load_served = 0.0
            steps += 1
            done = terminated or truncated
        rows.append({
            "seed": seed, "episode": episode + 1, "episode_seed": episode_seed,
            "steps": steps, "red_reward": totals["red"], "blue_reward": totals["blue"],
            "blackout": int(blackout), "detected": int(detected), "load_served_pct": load_served,
        })
    summary = {
        "seed": seed,
        "episodes": episodes,
        "mean_red_reward": float(np.mean([row["red_reward"] for row in rows])),
        "mean_blue_reward": float(np.mean([row["blue_reward"] for row in rows])),
        "blackout_rate": float(np.mean([row["blackout"] for row in rows])),
        "detection_rate": float(np.mean([row["detected"] for row in rows])),
        "mean_final_load_served_pct": float(np.mean([row["load_served_pct"] for row in rows])),
        "attack_actions": dict(sorted(attack_counts.items())),
        "defence_actions": dict(sorted(defence_counts.items())),
        "immune_memories_selected": len(env.immune_memory.memory_keys),
        "nonfinite_observation_values_sanitized": nonfinite_observations,
        "nonfinite_metric_values_sanitized": nonfinite_metrics,
    }
    return summary, rows


def run_evaluation(seeds: list[int], episodes: int, output_dir: Path, red_checkpoint: Path, blue_checkpoint: Path) -> dict:
    if episodes < 1 or len(seeds) < 2:
        raise ValueError("multi-seed evaluation requires at least two seeds and one episode")
    red = PathogenAgent(state_dim=293)
    blue = ImmuneAgent(state_dim=299)
    if not red.load_checkpoint(str(red_checkpoint)):
        raise FileNotFoundError(red_checkpoint)
    if not blue.load_checkpoint(str(blue_checkpoint)):
        raise FileNotFoundError(blue_checkpoint)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries, rows = [], []
    for seed in seeds:
        summary, seed_rows = evaluate_seed(seed, episodes, red, blue, output_dir / f"immune_memory_seed_{seed}.json")
        summaries.append(summary)
        rows.extend(seed_rows)
    report = {
        "schema_version": "pypy.coevolution-evaluation.v1",
        "grid": "ieee39",
        "mode": "checkpoint_selection_and_stochastic_policy_evaluation",
        "training_performed": False,
        "policy_selection": {
            "pathogen": {"path": str(red_checkpoint), "sha256": sha256(red_checkpoint)},
            "immune": {"path": str(blue_checkpoint), "sha256": sha256(blue_checkpoint)},
        },
        "seeds": seeds,
        "episodes_per_seed": episodes,
        "seed_results": summaries,
        "aggregate": {
            "mean_red_reward": float(np.mean([item["mean_red_reward"] for item in summaries])),
            "mean_blue_reward": float(np.mean([item["mean_blue_reward"] for item in summaries])),
            "mean_blackout_rate": float(np.mean([item["blackout_rate"] for item in summaries])),
            "mean_detection_rate": float(np.mean([item["detection_rate"] for item in summaries])),
            "mean_final_load_served_pct": float(np.mean([item["mean_final_load_served_pct"] for item in summaries])),
        },
        "limitations": [
            "This run selects existing co-evolved checkpoints; it does not retrain them.",
            "Results evaluate the isolated IEEE-39 co-evolution environment, not the MQTT production loop.",
        ],
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["reproducibility_digest"] = hashlib.sha256(canonical).hexdigest()
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (output_dir / "episodes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 999])
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/coevolution/latest"))
    parser.add_argument("--red-checkpoint", type=Path, default=Path("checkpoints/ppo_pathogen_coevolved.pt"))
    parser.add_argument("--blue-checkpoint", type=Path, default=Path("checkpoints/ppo_immune.pt"))
    args = parser.parse_args()
    report = run_evaluation(args.seeds, args.episodes, args.output_dir, args.red_checkpoint, args.blue_checkpoint)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
