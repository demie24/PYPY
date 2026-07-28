import os
import sys
import numpy as np
import pytest
import torch

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from core.adversarial.coevolution_env import CoevolutionEnv
from core.adversarial.immune_agent import ImmuneAgent
from core.adversarial.immune_memory import ImmuneMemory

def test_coevolution_env_reset():
    env = CoevolutionEnv()
    obs_dict, info = env.reset()
    
    assert "red" in obs_dict
    assert "blue" in obs_dict
    assert obs_dict["red"].shape == (293,)
    assert obs_dict["blue"].shape == (299,)
    assert isinstance(info, dict)

def test_coevolution_env_step():
    env = CoevolutionEnv()
    env.enable_confidence_filter = False
    env.reset()
    
    # Red action: FDIA (1) on Bus 5 (5) with magnitude 0.15
    red_action = {
        "type": 1,
        "target": 5,
        "magnitude": np.array([0.15], dtype=np.float32)
    }
    # Blue action: Quarantine telemetry (2) on Bus 5 (5)
    blue_action = {
        "type": 2,
        "target": 5
    }
    
    action_dict = {"red": red_action, "blue": blue_action}
    obs_dict, reward_dict, terminated, truncated, info = env.step(action_dict)
    
    # Assert output structures
    assert "red" in obs_dict
    assert "blue" in obs_dict
    assert "red" in reward_dict
    assert "blue" in reward_dict
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)
    
    # Assert that quarantining Bus 5 purged active FDIA on Bus 5
    assert 5 not in env.active_fdia

def test_coevolution_env_bus_isolation():
    env = CoevolutionEnv()
    env.enable_confidence_filter = False
    env.reset()
    
    # Blue action: Isolate Bus 3 (3)
    blue_action = {
        "type": 3,
        "target": 3
    }
    action_dict = {
        "red": {"type": 0, "target": 0, "magnitude": np.array([0.0], dtype=np.float32)},
        "blue": blue_action
    }
    
    env.step(action_dict)
    
    # Verify that breakers adjacent to Bus 3 were opened
    # Bus 3 connects to lines: check lines adjacent to Bus 3 are OPEN
    adjacent_tripped = False
    for line in env.topo.lines:
        if line["from"] == 3 or line["to"] == 3:
            if env.breakers[line["id"]] == "OPEN":
                adjacent_tripped = True
    assert adjacent_tripped

def test_immune_agent_policy():
    agent = ImmuneAgent(state_dim=299)
    state = np.random.randn(299).astype(np.float32)
    
    action, log_prob, value = agent.select_action(state)
    
    assert "type" in action
    assert "target" in action
    assert 0 <= action["type"] < 7
    assert 0 <= action["target"] < 46
    assert isinstance(log_prob, float)
    assert isinstance(value, float)

def test_immune_memory_database():
    temp_file = os.path.join(current_dir, "temp_test_immune_memory.json")
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    try:
        memory = ImmuneMemory(persistence_file=temp_file, threshold=0.80)
        
        # Create fake deviation vector (124 dims)
        fake_dev = np.random.randn(124).astype(np.float32)
        
        # Store mitigation action
        fake_mitigation = {"type": 2, "target": 10}
        memory.store(fake_dev, category=1, mitigation_action=fake_mitigation)
        
        # Query memory
        recall_flags, matched = memory.query(fake_dev)
        
        assert recall_flags.shape == (6,)
        assert len(memory.memory_keys) == 1
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
