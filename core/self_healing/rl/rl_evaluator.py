import os
import sys
import json
import logging
import numpy as np
import torch

# Setup paths to import core files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..")))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "digital_twin")))

from core.self_healing.rl.ppo_agent import PPOAgent
from core.self_healing.rl.dqn_agent import DQNAgent
from core.self_healing.rl_environment import GridRLEnvironment
from core.self_healing.rl.rl_trainer import get_target_for_action

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("self_healing.rl.rl_evaluator")

def evaluate_agent(agent_type: str = "PPO", num_trials: int = 10, max_steps: int = 10) -> dict:
    logger.info(f"Evaluating {agent_type} agent over {num_trials} trials...")
    
    env = GridRLEnvironment(is_live_mode=False)
    state_dim = 72
    action_dim = 10
    
    models_dir = os.path.abspath(os.path.join(CURRENT_DIR, "..", "models"))
    checkpoint_name = "ppo_self_healing.pt" if agent_type == "PPO" else "dqn_self_healing.pt"
    checkpoint_path = os.path.join(models_dir, checkpoint_name)
    
    # Initialize and load agent
    if agent_type == "PPO":
        agent = PPOAgent(state_dim=state_dim, action_dim=action_dim)
        loaded = agent.load_checkpoint(checkpoint_path)
    else:
        agent = DQNAgent(state_dim=state_dim, action_dim=action_dim)
        loaded = agent.load_checkpoint(checkpoint_path)
        
    if not loaded:
        logger.warning(f"Could not load checkpoint for {agent_type} at {checkpoint_path}. Evaluating untrained agent.")

    trial_rewards = []
    trial_violations = []
    trial_restoration_success = []
    
    # Evaluation scenarios list
    scenarios = ["LINE_FAULT", "CYBER_ATTACK", "OVERLOAD"]
    
    for trial in range(1, num_trials + 1):
        state, info = env.reset()
        
        # Select scenario deterministically based on trial index
        scenario = scenarios[trial % len(scenarios)]
        
        if scenario == "LINE_FAULT":
            env.sandbox_breakers["L4_5"] = "OPEN"
            env.latest_telemetry = env._get_sandbox_telemetry_snapshot()
            state = env.encoder.encode_state(telemetry=env.latest_telemetry)
        elif scenario == "CYBER_ATTACK":
            env.latest_trust_scores = {
                "bus_trust": {f"Bus_{i}": 100.0 for i in range(1, 10)},
                "line_trust": {lid: 100.0 for lid in env.sandbox_breakers.keys()}
            }
            env.latest_trust_scores["bus_trust"]["Bus_5"] = 25.0
            state = env.encoder.encode_state(telemetry=env._get_sandbox_telemetry_snapshot(), trust_scores=env.latest_trust_scores)
        elif scenario == "OVERLOAD":
            env.sandbox_breakers["L7_8"] = "OPEN"
            env.latest_telemetry = env._get_sandbox_telemetry_snapshot()
            state = env.encoder.encode_state(telemetry=env.latest_telemetry)
            
        trial_reward = 0.0
        trial_violation_count = 0
        restored = False
        
        for step in range(max_steps):
            # Select action deterministically
            if agent_type == "PPO":
                action_id, _, _ = agent.select_action(state, evaluation=True)
            else:
                action_id, _ = agent.select_action(state, evaluation=True)
                
            target = get_target_for_action(action_id, state, env)
            
            # Step environment
            next_state, reward, terminated, truncated, info_step = env.step(action_id, target)
            
            # Check for safety filter rejection
            if not info_step.get("action_allowed", True):
                trial_violation_count += 1
                action_id = 0
                reward, _ = env.reward_engine.compute_reward(state, next_state, action_id, rollback_occurred=True)
                
            trial_reward += reward
            
            # Check if all customer loads are healthy (voltage > 0.90 pu)
            curr_voltages = next_state[0:9]
            load_bus_indices = [4, 5, 7] # Bus 5, 6, 8
            if np.all(curr_voltages[load_bus_indices] > 0.90) and not any(v < 0.20 for v in curr_voltages):
                restored = True
                
            state = next_state
            if terminated or truncated:
                break
                
        trial_rewards.append(trial_reward)
        trial_violations.append(trial_violation_count)
        trial_restoration_success.append(1.0 if restored else 0.0)
        
        logger.info(f"Trial {trial}/{num_trials} | Scenario: {scenario} | Steps: {step+1} | Reward: {trial_reward:.2f} | Violations: {trial_violation_count} | Restored: {restored}")

    metrics = {
        "agent_type": agent_type,
        "num_trials": num_trials,
        "mean_reward": float(np.mean(trial_rewards)),
        "std_reward": float(np.std(trial_rewards)),
        "mean_violations": float(np.mean(trial_violations)),
        "restoration_rate": float(np.mean(trial_restoration_success)),
    }
    
    logger.info(f"Evaluation Summary for {agent_type}:")
    logger.info(f"  - Mean Reward: {metrics['mean_reward']:.2f}")
    logger.info(f"  - Mean Violations: {metrics['mean_violations']:.2f}")
    logger.info(f"  - Restoration Success Rate: {metrics['restoration_rate']*100:.1f}%")
    
    # Save evaluation results to JSON file
    results_path = os.path.join(models_dir, f"{agent_type.lower()}_evaluation_results.json")
    with open(results_path, "w") as f:
        json.dump(metrics, f, indent=4)
    logger.info(f"Evaluation metrics saved to {results_path}")
    
    return metrics

if __name__ == "__main__":
    agent = "PPO"
    if len(sys.argv) > 1:
        agent = sys.argv[1].upper()
    evaluate_agent(agent_type=agent)
