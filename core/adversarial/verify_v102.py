import os
import sys
import numpy as np

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from core.adversarial.imperfect_pathogen_env import ImperfectPathogenEnv
from core.adversarial.imperfect_pathogen_agent import ImperfectPathogenAgent

def verify_v102_system():
    print("Verifying PYPY V10.2 Imperfect Pathogen System Integration...")
    
    # 1. Test Environment with Mode B
    env_b = ImperfectPathogenEnv(mode="B")
    obs, info = env_b.reset()
    
    assert obs.shape == (293,)
    assert isinstance(info, dict)
    
    # Check that cyber states are zeroed under Mode B
    # Trust scores are at index 248:287
    assert np.all(obs[248:287] == 0.0)
    
    # Test step execution
    action = {"type": 5, "target": 25, "magnitude": np.array([0.0], dtype=np.float32)} # SCAN_BUS
    next_obs, reward, terminated, truncated, step_info = env_b.step(action)
    
    assert next_obs.shape == (293,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert "visibility" in step_info
    
    # 2. Test Recurrent Agent
    agent = ImperfectPathogenAgent()
    prev_action = 0
    prev_belief = np.zeros(64, dtype=np.float32)
    
    action_sel, log_prob, val, next_belief = agent.select_action(obs, prev_action, prev_belief)
    
    assert "type" in action_sel
    assert "target" in action_sel
    assert 0 <= action_sel["type"] < 8
    assert next_belief.shape == (64,)
    
    # 3. Test Mode C (Restricted)
    env_c = ImperfectPathogenEnv(mode="C")
    obs_c, _ = env_c.reset()
    # Telemetry at uncompromised nodes (e.g. Bus 10) must be default/masked
    # Bus 10 voltage at index 10 should be 1.0 (with noise, so roughly 1.0)
    assert abs(obs_c[10] - 1.0) < 0.15 # Allow noise variance window
    
    print("Integration Verification: ALL CHECKS PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    verify_v102_system()
