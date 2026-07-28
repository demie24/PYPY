import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)

def run_statistical_validation():
    print("Running Statistical Validation and Comparison Plot Generation...")
    
    # Load raw data
    baselines = np.load(os.path.join(current_dir, "baseline_raw_data.npz"))
    multiseed = np.load(os.path.join(current_dir, "multiseed_raw_data.npz"))
    
    # Extract baseline arrays
    r_rewards = baselines["random_rewards"]
    r_blackouts = baselines["random_blackouts"]
    r_stealths = baselines["random_stealths"]
    r_bypasses = baselines["random_bypasses"]
    
    h_rewards = baselines["heuristic_rewards"]
    h_blackouts = baselines["heuristic_blackouts"]
    h_stealths = baselines["heuristic_stealths"]
    h_bypasses = baselines["heuristic_bypasses"]
    
    # Extract PPO multiseed matrices (shape: 5, 1000)
    ppo_rewards = multiseed["rewards"]
    ppo_blackouts = multiseed["blackouts"]
    ppo_stealths = multiseed["stealths"]
    ppo_bypasses = multiseed["bypasses"]
    
    # We take the mean across seeds at each episode for plotting comparison
    ppo_rewards_mean = np.mean(ppo_rewards, axis=0)
    ppo_blackouts_mean = np.mean(ppo_blackouts, axis=0)
    ppo_stealths_mean = np.mean(ppo_stealths, axis=0)
    ppo_bypasses_mean = np.mean(ppo_bypasses, axis=0)
    
    # Perform significance testing (Welch's t-test on the last 100 episodes)
    # Extract the last 100 episodes of all seeds combined vs baselines
    ppo_last100_rewards = ppo_rewards[:, -100:].flatten()
    ppo_last100_blackouts = ppo_blackouts[:, -100:].flatten()
    ppo_last100_stealths = ppo_stealths[:, -100:].flatten()
    
    r_last100_rewards = r_rewards[-100:]
    r_last100_blackouts = r_blackouts[-100:]
    r_last100_stealths = r_stealths[-100:]
    
    h_last100_rewards = h_rewards[-100:]
    h_last100_blackouts = h_blackouts[-100:]
    h_last100_stealths = h_stealths[-100:]
    
    # T-tests: PPO vs Random
    t_rev_rand, p_rev_rand = stats.ttest_ind(ppo_last100_rewards, r_last100_rewards, equal_var=False)
    t_bo_rand, p_bo_rand = stats.ttest_ind(ppo_last100_blackouts, r_last100_blackouts, equal_var=False)
    t_st_rand, p_st_rand = stats.ttest_ind(ppo_last100_stealths, r_last100_stealths, equal_var=False)
    
    # T-tests: PPO vs Heuristic
    t_rev_heur, p_rev_heur = stats.ttest_ind(ppo_last100_rewards, h_last100_rewards, equal_var=False)
    t_bo_heur, p_bo_heur = stats.ttest_ind(ppo_last100_blackouts, h_last100_blackouts, equal_var=False)
    t_st_heur, p_st_heur = stats.ttest_ind(ppo_last100_stealths, h_last100_stealths, equal_var=False)
    
    # Convert nans to 1.0 p-value if constant arrays
    p_bo_rand = 1.0 if np.isnan(p_bo_rand) else float(p_bo_rand)
    p_st_rand = 1.0 if np.isnan(p_st_rand) else float(p_st_rand)
    p_bo_heur = 1.0 if np.isnan(p_bo_heur) else float(p_bo_heur)
    p_st_heur = 1.0 if np.isnan(p_st_heur) else float(p_st_heur)
    
    report = {
        "ppo_vs_random": {
            "reward": {"t_statistic": float(t_rev_rand), "p_value": float(p_rev_rand), "significant": bool(p_rev_rand < 0.05)},
            "blackout_rate": {"t_statistic": float(t_bo_rand), "p_value": float(p_bo_rand), "significant": bool(p_bo_rand < 0.05)},
            "stealth_score": {"t_statistic": float(t_st_rand), "p_value": float(p_st_rand), "significant": bool(p_st_rand < 0.05)}
        },
        "ppo_vs_heuristic": {
            "reward": {"t_statistic": float(t_rev_heur), "p_value": float(p_rev_heur), "significant": bool(p_rev_heur < 0.05)},
            "blackout_rate": {"t_statistic": float(t_bo_heur), "p_value": float(p_bo_heur), "significant": bool(p_bo_heur < 0.05)},
            "stealth_score": {"t_statistic": float(t_st_heur), "p_value": float(p_st_heur), "significant": bool(p_st_heur < 0.05)}
        }
    }
    
    with open(os.path.join(current_dir, "statistical_validation_report.json"), "w") as f:
        json.dump(report, f, indent=4)
        
    # Generate publication-quality comparison figures
    num_episodes = ppo_rewards.shape[1]
    episodes = np.arange(1, num_episodes + 1)
    window = min(100, num_episodes)
    
    # 1. Blackout Rate Comparison Plot
    plt.figure()
    plt.plot(episodes, pd.Series(ppo_blackouts_mean).rolling(window, min_periods=1).mean() * 100, color="#1abc9c", linewidth=2.5, label="PPO Pathogen (Mean)")
    plt.plot(episodes, pd.Series(r_blackouts[:num_episodes]).rolling(window, min_periods=1).mean() * 100, color="#7f8c8d", linestyle="--", linewidth=1.5, label="Random Attacker")
    plt.plot(episodes, pd.Series(h_blackouts[:num_episodes]).rolling(window, min_periods=1).mean() * 100, color="#e74c3c", linestyle=":", linewidth=2, label="Heuristic Attacker")
    plt.title(f"Blackout Success Rate Comparison (Rolling {window})", fontsize=12, fontweight="bold")
    plt.xlabel("Episode")
    plt.ylabel("Blackout Success Rate (%)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(current_dir, "figures", "blackout_rate_comparison.png"), dpi=300)
    plt.close()
    
    # 2. Reward Comparison Plot
    plt.figure()
    plt.plot(episodes, pd.Series(ppo_rewards_mean).rolling(50, min_periods=1).mean(), color="#3498db", linewidth=2.5, label="PPO Pathogen (Mean)")
    plt.plot(episodes, pd.Series(r_rewards[:num_episodes]).rolling(50, min_periods=1).mean(), color="#7f8c8d", linestyle="--", linewidth=1.5, label="Random Attacker")
    plt.plot(episodes, pd.Series(h_rewards[:num_episodes]).rolling(50, min_periods=1).mean(), color="#e74c3c", linestyle=":", linewidth=2, label="Heuristic Attacker")
    plt.title("Pathogen Reward Development (Rolling 50)", fontsize=12, fontweight="bold")
    plt.xlabel("Episode")
    plt.ylabel("Average Episode Reward")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(current_dir, "figures", "reward_comparison.png"), dpi=300)
    plt.close()
    
    # 3. Stealth Comparison Plot
    plt.figure()
    plt.plot(episodes, pd.Series(ppo_stealths_mean).rolling(window, min_periods=1).mean() * 100, color="#2ecc71", linewidth=2.5, label="PPO Pathogen (Mean)")
    plt.plot(episodes, pd.Series(r_stealths[:num_episodes]).rolling(window, min_periods=1).mean() * 100, color="#7f8c8d", linestyle="--", linewidth=1.5, label="Random Attacker")
    plt.plot(episodes, pd.Series(h_stealths[:num_episodes]).rolling(window, min_periods=1).mean() * 100, color="#e74c3c", linestyle=":", linewidth=2, label="Heuristic Attacker")
    plt.title(f"Telemetry Stealth Ratio Comparison (Rolling {window})", fontsize=12, fontweight="bold")
    plt.xlabel("Episode")
    plt.ylabel("Stealth Ratio (%)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(current_dir, "figures", "stealth_comparison.png"), dpi=300)
    plt.close()
    
    # 4. Consensus Bypass Comparison Plot
    plt.figure()
    plt.plot(episodes, pd.Series(ppo_bypasses_mean).rolling(window, min_periods=1).mean() * 100, color="#9b59b6", linewidth=2.5, label="PPO Pathogen (Mean)")
    plt.plot(episodes, pd.Series(r_bypasses[:num_episodes]).rolling(window, min_periods=1).mean() * 100, color="#7f8c8d", linestyle="--", linewidth=1.5, label="Random Attacker")
    plt.plot(episodes, pd.Series(h_bypasses[:num_episodes]).rolling(window, min_periods=1).mean() * 100, color="#e74c3c", linestyle=":", linewidth=2, label="Heuristic Attacker")
    plt.title(f"Defense Consensus Bypass Rate Comparison (Rolling {window})", fontsize=12, fontweight="bold")
    plt.xlabel("Episode")
    plt.ylabel("Bypass Rate (%)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(current_dir, "figures", "consensus_bypass_comparison.png"), dpi=300)
    plt.close()
    
    print("Statistical Validation and Comparison Plots successfully generated.")

if __name__ == "__main__":
    run_statistical_validation()
