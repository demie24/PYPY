import os
import sys
import json
import random
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)

from core.adversarial.pathogen_env import PathogenEnv

def run_random_baseline(env, num_episodes=1000):
    print("Running Random Baseline Attacker...")
    rewards = []
    blackouts = []
    stealths = []
    bypasses = []
    disruptions = []
    
    for ep in range(1, num_episodes + 1):
        state, info = env.reset()
        done = False
        ep_reward = 0.0
        ep_steps = 0
        ep_stealth_steps = 0
        ep_blackout = False
        ep_disruption = 0.0
        ep_detected = False
        
        while not done:
            action = env.action_space.sample()
            next_state, reward, terminated, truncated, step_info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
            ep_steps += 1
            ep_disruption += step_info.get("disruption", 0.0)
            
            decision = step_info.get("global_decision", "NORMAL")
            if decision in ["ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]:
                ep_detected = True
            if decision in ["NORMAL", "WARNING", "ANOMALY"]:
                ep_stealth_steps += 1
            if step_info.get("blackout", False):
                ep_blackout = True
                
        rewards.append(ep_reward)
        blackouts.append(1.0 if ep_blackout else 0.0)
        stealths.append(ep_stealth_steps / ep_steps if ep_steps > 0 else 0.0)
        bypasses.append(1.0 if (ep_blackout and not ep_detected) else 0.0)
        disruptions.append(ep_disruption / ep_steps if ep_steps > 0 else 0.0)
        
    return {
        "blackout_rate": float(np.mean(blackouts)),
        "average_reward": float(np.mean(rewards)),
        "stealth_score": float(np.mean(stealths)),
        "consensus_bypass": float(np.sum(bypasses) / max(1, np.sum(blackouts))),
        "disruption_score": float(np.mean(disruptions)),
        "rewards": rewards,
        "blackouts": blackouts,
        "stealths": stealths,
        "bypasses": bypasses,
        "disruptions": disruptions
    }

def run_heuristic_baseline(env, num_episodes=1000):
    print("Running Heuristic Baseline Attacker...")
    # Heuristic strategy: target top GNN critical nodes (25, 28) and trip lines (L_line_1, L_line_6, L_line_4)
    # Target indices: Bus 25 is index 25, Bus 28 is index 28.
    # Lines: L_line_1 is target index 39 + 1 = 40, L_line_6 is target index 39 + 6 = 45, L_line_4 is index 39 + 4 = 43.
    critical_targets = [25, 28, 40, 43, 45]
    
    rewards = []
    blackouts = []
    stealths = []
    bypasses = []
    disruptions = []
    
    for ep in range(1, num_episodes + 1):
        state, info = env.reset()
        done = False
        ep_reward = 0.0
        ep_steps = 0
        ep_stealth_steps = 0
        ep_blackout = False
        ep_disruption = 0.0
        ep_detected = False
        
        while not done:
            # Deterministic/semi-deterministic heuristic selection
            target = random.choice(critical_targets)
            if target >= 39:
                act_type = 4 # TRIP_LINE
            else:
                act_type = 1 # FDIA
            
            action = {
                "type": act_type,
                "target": target,
                "magnitude": np.array([0.20 if random.random() > 0.5 else -0.20], dtype=np.float32)
            }
            
            next_state, reward, terminated, truncated, step_info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
            ep_steps += 1
            ep_disruption += step_info.get("disruption", 0.0)
            
            decision = step_info.get("global_decision", "NORMAL")
            if decision in ["ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]:
                ep_detected = True
            if decision in ["NORMAL", "WARNING", "ANOMALY"]:
                ep_stealth_steps += 1
            if step_info.get("blackout", False):
                ep_blackout = True
                
        rewards.append(ep_reward)
        blackouts.append(1.0 if ep_blackout else 0.0)
        stealths.append(ep_stealth_steps / ep_steps if ep_steps > 0 else 0.0)
        bypasses.append(1.0 if (ep_blackout and not ep_detected) else 0.0)
        disruptions.append(ep_disruption / ep_steps if ep_steps > 0 else 0.0)
        
    return {
        "blackout_rate": float(np.mean(blackouts)),
        "average_reward": float(np.mean(rewards)),
        "stealth_score": float(np.mean(stealths)),
        "consensus_bypass": float(np.sum(bypasses) / max(1, np.sum(blackouts))),
        "disruption_score": float(np.mean(disruptions)),
        "rewards": rewards,
        "blackouts": blackouts,
        "stealths": stealths,
        "bypasses": bypasses,
        "disruptions": disruptions
    }

if __name__ == "__main__":
    env = PathogenEnv()
    random_res = run_random_baseline(env)
    heuristic_res = run_heuristic_baseline(env)
    
    # Save raw outputs (excluding lists for clean JSON)
    clean_random = {k: v for k, v in random_res.items() if not isinstance(v, list)}
    clean_heuristic = {k: v for k, v in heuristic_res.items() if not isinstance(v, list)}
    
    report = {
        "random_attacker": clean_random,
        "heuristic_attacker": clean_heuristic
    }
    
    os.makedirs(os.path.join(current_dir, "figures"), exist_ok=True)
    with open(os.path.join(current_dir, "baseline_comparison_report.json"), "w") as f:
        json.dump(report, f, indent=4)
        
    # Save the raw reward/blackout lists for significance testing later
    np.savez(os.path.join(current_dir, "baseline_raw_data.npz"),
             random_rewards=random_res["rewards"],
             random_blackouts=random_res["blackouts"],
             random_stealths=random_res["stealths"],
             random_bypasses=random_res["bypasses"],
             heuristic_rewards=heuristic_res["rewards"],
             heuristic_blackouts=heuristic_res["blackouts"],
             heuristic_stealths=heuristic_res["stealths"],
             heuristic_bypasses=heuristic_res["bypasses"])
             
    print("Baseline Runner completed successfully. Saved baseline_comparison_report.json.")
