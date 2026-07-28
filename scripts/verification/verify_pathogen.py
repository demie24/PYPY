import os
import sys

# Setup paths to import adversarial modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

from pathogen_env import PathogenEnv
from pathogen_agent import PathogenAgent
from pathogen_trainer import PathogenTrainer

def verify_pathogen_subsystem():
    print("====================================================")
    print("VERIFYING PYPY v9.7.1 ARTIFICIAL PATHOGEN SUBSYSTEM")
    print("====================================================")
    
    # 1. Test Gymnasium Environment Initialization
    print("\n--- Phase 1: Environment Initialization ---")
    env = PathogenEnv()
    obs, info = env.reset()
    
    print(f"Observation space shape: {env.observation_space.shape}")
    print(f"Observation vector length: {len(obs)}")
    print(f"Initial Info Payload: {info}")
    
    assert len(obs) == 293, f"Expected 293 dimensions, got {len(obs)}"
    print(">>> Phase 1 Passed!")

    # 2. Test Pathogen Agent Policy Head Output Formatting
    print("\n--- Phase 2: Agent Architecture Verification ---")
    agent = PathogenAgent(state_dim=293)
    action, log_prob, value = agent.select_action(obs, evaluation=False)
    
    print(f"Sampled Action Dict: {action}")
    print(f"  - Action Type: {action['type']} (Type: {type(action['type'])})")
    print(f"  - Target Component: {action['target']} (Type: {type(action['target'])})")
    print(f"  - Falsification Magnitude: {action['magnitude']} (Shape: {action['magnitude'].shape})")
    print(f"Action Log-Prob: {log_prob:.4f}")
    print(f"State Value Estimate: {value:.4f}")
    
    assert 0 <= action['type'] <= 4, f"Action type out of range: {action['type']}"
    assert 0 <= action['target'] <= 45, f"Action target out of range: {action['target']}"
    assert -0.20 <= action['magnitude'][0] <= 0.20, f"Action magnitude out of range: {action['magnitude'][0]}"
    print(">>> Phase 2 Passed!")

    # 3. Test Closed-Loop Step Transitions
    print("\n--- Phase 3: Transition Step Verification ---")
    next_obs, reward, terminated, truncated, step_info = env.step(action)
    
    print(f"Transition Outputs:")
    print(f"  - Next Obs Shape: {next_obs.shape}")
    print(f"  - Reward: {reward:.4f}")
    print(f"  - Terminated: {terminated}")
    print(f"  - Step Info Payload: {step_info}")
    
    assert len(next_obs) == 293, f"Expected next obs 293, got {len(next_obs)}"
    print(">>> Phase 3 Passed!")

    # 4. Test Multi-Episode Training Run (Trainer dry run)
    print("\n--- Phase 4: Trainer Integration dry run ---")
    trainer = PathogenTrainer()
    # Run 3 episodes to verify training update math completes successfully
    trainer.train(num_episodes=3, checkpoint_interval=2)
    print(">>> Phase 4 Passed!")

    print("\n====================================================")
    print("ALL PATHOGEN SUBSYSTEM VERIFICATIONS PASSED SUCCESSFULLY!")
    print("====================================================")

if __name__ == "__main__":
    verify_pathogen_subsystem()
