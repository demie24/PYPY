import os
import sys
import numpy as np
import pytest
import torch

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from core.adversarial.observation_masker import ObservationMasker
from core.adversarial.belief_encoder import GRUBeliefEncoder
from core.adversarial.reconnaissance_engine import ReconnaissanceEngine
from core.adversarial.imperfect_pathogen_env import ImperfectPathogenEnv
from core.adversarial.imperfect_pathogen_agent import ImperfectPathogenAgent

def test_observation_masking():
    masker = ObservationMasker()
    true_obs = np.ones(293, dtype=np.float32)
    true_obs[248:287] = 0.95 # trust scores
    
    # Test Mode B masking
    obs_b = masker.apply_mask(true_obs, mode="B", visibility=0.5, compromised_buses={25}, active_dos=set())
    assert obs_b.shape == (293,)
    assert np.all(obs_b[248:287] == 0.0) # cyber variables zeroed
    
    # Test Mode C masking
    obs_c = masker.apply_mask(true_obs, mode="C", visibility=0.2, compromised_buses={25}, active_dos=set())
    # Uncompromised node voltage (index 10) must be default 1.0 (with noise, so close to 1.0)
    assert abs(obs_c[10] - 1.0) < 0.15

def test_belief_encoder():
    encoder = GRUBeliefEncoder(obs_dim=293, action_dim=8, hidden_dim=64)
    obs = torch.randn(1, 293)
    prev_action = torch.LongTensor([2])
    prev_belief = torch.zeros(1, 64)
    
    new_belief = encoder(obs, prev_action, prev_belief)
    assert new_belief.shape == (1, 64)

def test_reconnaissance_engine():
    engine = ReconnaissanceEngine()
    true_state = np.ones(293, dtype=np.float32)
    
    # SCAN_BUS on Bus 25
    res = engine.execute_scan(action_type=5, target=25, true_state=true_state)
    assert "estimated_state" in res
    assert "uncertainty" in res
    assert "information_gain" in res
    assert res["information_gain"] > 0.0

def test_imperfect_env_step():
    env = ImperfectPathogenEnv(mode="B")
    obs, info = env.reset()
    
    action = {"type": 5, "target": 25, "magnitude": np.array([0.0], dtype=np.float32)}
    next_obs, reward, terminated, truncated, step_info = env.step(action)
    
    assert next_obs.shape == (293,)
    assert isinstance(reward, float)
    assert "visibility" in step_info

def test_imperfect_agent():
    agent = ImperfectPathogenAgent()
    obs = np.ones(293, dtype=np.float32)
    prev_action = 0
    prev_belief = np.zeros(64, dtype=np.float32)
    
    action_sel, log_prob, val, next_belief = agent.select_action(obs, prev_action, prev_belief)
    
    assert "type" in action_sel
    assert "target" in action_sel
    assert next_belief.shape == (64,)

def test_agent_update():
    agent = ImperfectPathogenAgent()
    
    # Create mock trajectory of 5 steps
    obs = [np.ones(293, dtype=np.float32) for _ in range(5)]
    prev_actions = [0, 1, 2, 3, 4]
    act_types = [1, 2, 3, 4, 5]
    act_targets = [10, 20, 30, 40, 25]
    act_mags = [np.array([0.05], dtype=np.float32), np.array([-0.05], dtype=np.float32), np.array([0.0], dtype=np.float32), np.array([0.1], dtype=np.float32), np.array([-0.1], dtype=np.float32)]
    old_log_probs = [-0.5, -0.6, -0.4, -0.7, -0.3]
    values = [0.1, 0.2, 0.15, 0.3, 0.25]
    rewards = [1.0, -1.0, 5.0, -2.0, 10.0]
    dones = [False, False, False, False, True]
    
    memory = (obs, prev_actions, act_types, act_targets, act_mags, old_log_probs, values, rewards, dones)
    
    actor_loss, critic_loss = agent.update(memory, ppo_epochs=2)
    assert isinstance(actor_loss, float)
    assert isinstance(critic_loss, float)

