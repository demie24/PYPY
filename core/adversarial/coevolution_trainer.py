import os
import sys
import json
import argparse
import random
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)

from core.adversarial.coevolution_env import CoevolutionEnv
from core.adversarial.pathogen_agent import PathogenAgent
from core.adversarial.immune_agent import ImmuneAgent

def run_coevolution_training(num_episodes=200, resume=False):
    print(f"Starting PYPY V9.7.2 Co-Evolutionary League Training for {num_episodes} episodes...")
    
    # Setup directories
    checkpoints_dir = os.path.join(project_root, "checkpoints")
    league_red_dir = os.path.join(checkpoints_dir, "league", "red")
    league_blue_dir = os.path.join(checkpoints_dir, "league", "blue")
    os.makedirs(league_red_dir, exist_ok=True)
    os.makedirs(league_blue_dir, exist_ok=True)
    
    analytics_dir = os.path.join(project_root, "analytics")
    os.makedirs(analytics_dir, exist_ok=True)
    
    env = CoevolutionEnv()
    
    # Initialize agents
    red_agent = PathogenAgent(state_dim=293)
    blue_agent = ImmuneAgent(state_dim=299)
    
    # Load past pathogen checkpoint if available to initialize attacker
    past_checkpoint = os.path.join(checkpoints_dir, "ppo_pathogen.pt")
    if os.path.exists(past_checkpoint):
        print(f"Initializing Red Agent from validated checkpoint: {past_checkpoint}")
        red_agent.load_checkpoint(past_checkpoint)
    
    # League pools of models
    red_league_checkpoints = []
    blue_league_checkpoints = []
    
    # Memory buffers for PPO updates
    # Red Agent Buffers
    red_states, red_act_types, red_act_targets, red_act_mags, red_log_probs, red_values, red_rewards, red_dones = [], [], [], [], [], [], [], []
    # Blue Agent Buffers
    blue_states, blue_act_types, blue_act_targets, blue_log_probs, blue_values, blue_rewards, blue_dones = [], [], [], [], [], [], []
    
    # Telemetry data cache for VAE training
    vae_training_data = []
    vae_trained = False
    
    # Logging metrics
    history_red_rewards = []
    history_blue_rewards = []
    history_blackouts = []
    history_stealth = []
    history_bypasses = []
    
    start_ep = 1
    csv_path = os.path.join(analytics_dir, "coevolution_learning_curve.csv")
    
    if resume:
        import re
        red_eps = []
        if os.path.exists(league_red_dir):
            for f in os.listdir(league_red_dir):
                m = re.match(r"ppo_red_ep(\d+)\.pt", f)
                if m:
                    red_eps.append(int(m.group(1)))
        blue_eps = []
        if os.path.exists(league_blue_dir):
            for f in os.listdir(league_blue_dir):
                m = re.match(r"ppo_blue_ep(\d+)\.pt", f)
                if m:
                    blue_eps.append(int(m.group(1)))
                    
        common_eps = set(red_eps).intersection(set(blue_eps))
        if common_eps:
            max_ep = max(common_eps)
            print(f"Resuming coevolution training from episode {max_ep}...")
            
            # Load checkpoints
            red_checkpoint_path = os.path.join(league_red_dir, f"ppo_red_ep{max_ep}.pt")
            blue_checkpoint_path = os.path.join(league_blue_dir, f"ppo_blue_ep{max_ep}.pt")
            
            red_agent.load_checkpoint(red_checkpoint_path)
            blue_agent.load_checkpoint(blue_checkpoint_path)
            
            start_ep = max_ep + 1
            
            # Populate league lists up to max_ep
            for ep_num in sorted(list(common_eps)):
                if ep_num <= max_ep:
                    red_league_checkpoints.append(os.path.join(league_red_dir, f"ppo_red_ep{ep_num}.pt"))
                    blue_league_checkpoints.append(os.path.join(league_blue_dir, f"ppo_blue_ep{ep_num}.pt"))
            
            # Read and filter CSV file if exists
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    df = df[df["episode"] < start_ep]
                    df.to_csv(csv_path, index=False)
                    history_red_rewards = df["red_reward"].tolist()
                    history_blue_rewards = df["blue_reward"].tolist()
                    history_blackouts = df["blackout"].tolist()
                    history_stealth = df["stealth_rate"].tolist()
                    history_bypasses = df["consensus_bypass"].tolist()
                except Exception as e:
                    print(f"Error filtering learning curve CSV: {e}")
            vae_trained = True  # VAE model is already trained and on disk
        else:
            print("No matching checkpoints found to resume. Starting from episode 1.")
            resume = False
            
    if not resume:
        with open(csv_path, "w") as f:
            f.write("episode,red_reward,blue_reward,blackout,stealth_rate,consensus_bypass\n")
            
    for ep in range(start_ep, num_episodes + 1):
        obs_dict, info = env.reset()
        red_state = obs_dict["red"]
        blue_state = obs_dict["blue"]
        
        # Decide active opponent from league
        # Matchmaking: 80% past checkpoint (if available), 20% active policy
        active_red_agent = red_agent
        active_blue_agent = blue_agent
        
        if len(red_league_checkpoints) > 0 and random.random() < 0.8:
            # Create a temporary agent and load a random historical checkpoint
            active_red_agent = PathogenAgent(state_dim=293)
            active_red_agent.load_checkpoint(random.choice(red_league_checkpoints))
            
        if len(blue_league_checkpoints) > 0 and random.random() < 0.8:
            active_blue_agent = ImmuneAgent(state_dim=299)
            active_blue_agent.load_checkpoint(random.choice(blue_league_checkpoints))
            
        done = False
        ep_red_reward = 0.0
        ep_blue_reward = 0.0
        ep_steps = 0
        ep_stealth_steps = 0
        ep_blackout = False
        ep_detected = False
        
        # Curriculum target overrides
        # Stage 1: (Episodes 1-30) Rule-based pathogen
        is_stage_1 = (ep <= 30)
        
        while not done:
            # 1. Select Red Action (Pathogen)
            if is_stage_1:
                # Rule-based simple attacker: trip random lines, do FDIA on critical node 25
                target = random.choice([25, 28, 40, 43, 45])
                act_type = 4 if target >= 39 else 1
                red_action = {
                    "type": act_type,
                    "target": target,
                    "magnitude": np.array([0.20 if random.random() > 0.5 else -0.20], dtype=np.float32)
                }
                red_log_prob = 0.0
                red_value = 0.0
            else:
                red_action, red_log_prob, red_value = active_red_agent.select_action(red_state)
                
            # 2. Select Blue Action (Immune)
            # Check if there is a recalled action from memory
            recalled_action = info.get("recalled_action")
            if recalled_action is not None and not is_stage_1:
                blue_action = recalled_action
                blue_log_prob = 0.0
                blue_value = 0.0
            else:
                blue_action, blue_log_prob, blue_value = active_blue_agent.select_action(blue_state)
                
            # Step Environment
            joint_actions = {"red": red_action, "blue": blue_action}
            next_obs_dict, reward_dict, terminated, truncated, step_info = env.step(joint_actions)
            
            # Record VAE training deviations vector
            # SCADA deviations vector = [V-Vnom, P-Pnom, loadings]
            V_dev = next_obs_dict["red"][0:39] - env.V_nom
            P_dev = next_obs_dict["red"][39:78] - env.P_nom
            loadings = next_obs_dict["red"][78:124]
            X_dev = np.concatenate([V_dev, P_dev, loadings]).astype(np.float32)
            vae_training_data.append(X_dev)
            
            # Accumulate rewards & steps
            ep_red_reward += reward_dict["red"]
            ep_blue_reward += reward_dict["blue"]
            done = terminated or truncated
            ep_steps += 1
            
            decision = step_info.get("global_decision", "NORMAL")
            if decision in ["ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]:
                ep_detected = True
            if decision in ["NORMAL", "WARNING", "ANOMALY"]:
                ep_stealth_steps += 1
            if step_info.get("blackout", False):
                ep_blackout = True
                
            # Push to buffers (only for active training policies)
            if active_red_agent is red_agent and not is_stage_1:
                red_states.append(red_state)
                red_act_types.append(int(red_action["type"]))
                red_act_targets.append(int(red_action["target"]))
                red_act_mags.append(float(red_action["magnitude"][0]))
                red_log_probs.append(red_log_prob)
                red_values.append(red_value)
                red_rewards.append(reward_dict["red"])
                red_dones.append(done)
                
            if active_blue_agent is blue_agent:
                blue_states.append(blue_state)
                blue_act_types.append(int(blue_action["type"]))
                blue_act_targets.append(int(blue_action["target"]))
                blue_log_probs.append(blue_log_prob)
                blue_values.append(blue_value)
                blue_rewards.append(reward_dict["blue"])
                blue_dones.append(done)
                
            # Transition states
            red_state = next_obs_dict["red"]
            blue_state = next_obs_dict["blue"]
            info = step_info

        # --- END OF EPISODE UPDATES & VAE TRAINING ---
        # 1. Warm-up and train VAE
        if ep == 10 and not vae_trained:
            print("Warming up VAE: training on accumulated deviations data...")
            arr_data = np.array(vae_training_data, dtype=np.float32)
            env.immune_memory.train_vae(arr_data, epochs=40)
            vae_trained = True
            
        # 2. Alternating PPO Optimization Updates
        # Epoch 2N: Update Red
        # Epoch 2N+1: Update Blue
        if ep > 30: # Start updating after curriculum Stage 1
            if ep % 2 == 0:
                if len(red_states) > 16:
                    # Package memory
                    red_mem = (
                        np.array(red_states, dtype=np.float32),
                        np.array(red_act_types, dtype=np.int64),
                        np.array(red_act_targets, dtype=np.int64),
                        np.array(red_act_mags, dtype=np.float32),
                        np.array(red_log_probs, dtype=np.float32),
                        np.array(red_values, dtype=np.float32),
                        np.array(red_rewards, dtype=np.float32),
                        np.array(red_dones, dtype=np.float32)
                    )
                    red_agent.update(red_mem)
                    # Clear red memory
                    red_states.clear(); red_act_types.clear(); red_act_targets.clear(); red_act_mags.clear()
                    red_log_probs.clear(); red_values.clear(); red_rewards.clear(); red_dones.clear()
            else:
                if len(blue_states) > 16:
                    blue_mem = (
                        np.array(blue_states, dtype=np.float32),
                        np.array(blue_act_types, dtype=np.int64),
                        np.array(blue_act_targets, dtype=np.int64),
                        np.array(blue_log_probs, dtype=np.float32),
                        np.array(blue_values, dtype=np.float32),
                        np.array(blue_rewards, dtype=np.float32),
                        np.array(blue_dones, dtype=np.float32)
                    )
                    blue_agent.update(blue_mem)
                    # Clear blue memory
                    blue_states.clear(); blue_act_types.clear(); blue_act_targets.clear()
                    blue_log_probs.clear(); blue_values.clear(); blue_rewards.clear(); blue_dones.clear()

        # Log metrics
        stealth_rate = ep_stealth_steps / ep_steps if ep_steps > 0 else 0.0
        consensus_bypass = 1.0 if (ep_blackout and not ep_detected) else 0.0
        
        history_red_rewards.append(ep_red_reward)
        history_blue_rewards.append(ep_blue_reward)
        history_blackouts.append(1.0 if ep_blackout else 0.0)
        history_stealth.append(stealth_rate)
        history_bypasses.append(consensus_bypass)
        
        # Save to csv learning curves
        with open(csv_path, "a") as f:
            f.write(f"{ep},{ep_red_reward:.4f},{ep_blue_reward:.4f},{1 if ep_blackout else 0},{stealth_rate:.4f},{consensus_bypass:.4f}\n")
            
        # League Model Checkpoints Pool addition
        # Every 40 episodes, add checkpoint to league pool
        if ep % 40 == 0:
            red_cp_filename = f"ppo_red_ep{ep}.pt"
            blue_cp_filename = f"ppo_blue_ep{ep}.pt"
            
            red_agent.save_checkpoint(league_red_dir, red_cp_filename)
            blue_agent.save_checkpoint(league_blue_dir, blue_cp_filename)
            
            red_league_checkpoints.append(os.path.join(league_red_dir, red_cp_filename))
            blue_league_checkpoints.append(os.path.join(league_blue_dir, blue_cp_filename))
            
        if ep % 20 == 0:
            print(f"Ep {ep}/{num_episodes} | Red Reward: {np.mean(history_red_rewards[-20:]):.2f} | Blue Reward: {np.mean(history_blue_rewards[-20:]):.2f} | Blackout: {np.mean(history_blackouts[-20:])*100:.1f}% | Stealth: {np.mean(history_stealth[-20:])*100:.1f}%")
            
    # Save final model checkpoints
    red_agent.save_checkpoint(checkpoints_dir, "ppo_pathogen_coevolved.pt")
    blue_agent.save_checkpoint(checkpoints_dir, "ppo_immune.pt")
    
    # Save final co-evolution report
    report = {
        "final_episodes_run": num_episodes,
        "pathogen_average_reward": float(np.mean(history_red_rewards[-50:])),
        "immune_average_reward": float(np.mean(history_blue_rewards[-50:])),
        "blackout_rate": float(np.mean(history_blackouts[-50:])),
        "average_stealth": float(np.mean(history_stealth[-50:])),
        "consensus_bypass_rate": float(np.mean(history_bypasses[-50:])),
        "immune_memory_size": len(env.immune_memory.memory_keys)
    }
    with open(os.path.join(analytics_dir, "coevolution_summary_report.json"), "w") as f:
        json.dump(report, f, indent=4)
        
    # Generate Plot
    plt.figure(figsize=(10, 5))
    episodes_arr = np.arange(1, num_episodes + 1)
    plt.plot(episodes_arr, pd.Series(history_red_rewards).rolling(10, min_periods=1).mean(), color="#e74c3c", label="Pathogen Reward (Red)")
    plt.plot(episodes_arr, pd.Series(history_blue_rewards).rolling(10, min_periods=1).mean(), color="#3498db", label="Immune System Reward (Blue)")
    plt.title("Pathogen vs Immune System Co-Evolution Rewards (Rolling 10)")
    plt.xlabel("Episode")
    plt.ylabel("Episode Reward")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(analytics_dir, "coevolution_rewards_curve.png"), dpi=300)
    plt.close()
    
    print("Co-Evolution training run completed successfully. Generated curve & reports.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100, help="Number of coevolution episodes")
    parser.add_argument("--resume", action="store_true", help="Resume coevolution training from latest checkpoint")
    args = parser.parse_args()
    
    run_coevolution_training(args.episodes, resume=args.resume)
