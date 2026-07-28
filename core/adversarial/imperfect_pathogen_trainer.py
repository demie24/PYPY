import os
import sys
import json
import argparse
import random
import numpy as np
import torch
import pandas as pd
import matplotlib.pyplot as plt

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from core.adversarial.imperfect_pathogen_env import ImperfectPathogenEnv
from core.adversarial.imperfect_pathogen_agent import ImperfectPathogenAgent

def train_imperfect_pathogen(mode: str = "B", episodes: int = 100):
    print(f"Training Imperfect Pathogen in Mode {mode} for {episodes} episodes...")
    
    analytics_dir = os.path.join(project_root, "analytics")
    os.makedirs(analytics_dir, exist_ok=True)
    checkpoints_dir = os.path.join(project_root, "checkpoints")
    os.makedirs(checkpoints_dir, exist_ok=True)
    
    env = ImperfectPathogenEnv(mode=mode)
    agent = ImperfectPathogenAgent()
    
    csv_path = os.path.join(analytics_dir, "imperfect_learning_curve.csv")
    with open(csv_path, "w") as f:
        f.write("episode,reward,blackout,visibility,information_gain\n")
        
    history_rewards = []
    history_blackouts = []
    
    for ep in range(1, episodes + 1):
        obs, info = env.reset()
        
        prev_action = 0 # NO_ACTION
        prev_belief = np.zeros(64, dtype=np.float32)
        
        done = False
        ep_reward = 0.0
        ep_blackout = False
        ep_info_gain = 0.0
        steps = 0
        
        while not done:
            action, log_prob, val, belief = agent.select_action(obs, prev_action, prev_belief)
            
            # Execute step
            next_obs, reward, terminated, truncated, step_info = env.step(action)
            
            ep_reward += reward
            done = terminated or truncated
            steps += 1
            
            if step_info.get("blackout", False):
                ep_blackout = True
            ep_info_gain += step_info.get("information_gain", 0.0)
            
            obs = next_obs
            prev_action = int(action["type"])
            prev_belief = belief
            
        history_rewards.append(ep_reward)
        history_blackouts.append(1.0 if ep_blackout else 0.0)
        
        with open(csv_path, "a") as f:
            f.write(f"{ep},{ep_reward:.4f},{1 if ep_blackout else 0},{env.visibility:.4f},{ep_info_gain:.4f}\n")
            
        if ep % 20 == 0:
            print(f"Ep {ep}/{episodes} | Avg Reward: {np.mean(history_rewards[-20:]):.2f} | Blackout: {np.mean(history_blackouts[-20:])*100:.1f}% | Visibility: {env.visibility:.2f}")

    # Save final model
    agent.save_checkpoint(checkpoints_dir, f"ppo_imperfect_pathogen_mode_{mode}.pt")
    
    # Plot curves
    plt.figure(figsize=(10, 5))
    plt.plot(pd.Series(history_rewards).rolling(10, min_periods=1).mean(), color="#e74c3c", label="Attacker Reward")
    plt.title(f"Imperfect Pathogen Learning Curve (Mode {mode})")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(analytics_dir, f"imperfect_learning_curve_mode_{mode}.png"), dpi=300)
    plt.close()
    
    print(f"Training complete for Mode {mode}. Checkpoint saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="B", help="Attacker mode: A, B, C, D")
    parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes")
    args = parser.parse_args()
    
    train_imperfect_pathogen(args.mode, args.episodes)
