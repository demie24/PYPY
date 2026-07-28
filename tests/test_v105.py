import os
import sys
import numpy as np
import pytest

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from core.digital_twin.grid_topology import GridTopology
from core.analytics.som_vulnerability_engine import SomVulnerabilityEngine, CustomSOM
from core.adversarial.concurrent_attack_engine import ConcurrentAttackEngine
from core.adversarial.imperfect_pathogen_env import ImperfectPathogenEnv

def test_custom_som_logic():
    # Test basic SOM vector mapping
    np.random.seed(42)
    data = np.random.rand(10, 4) # 10 samples, 4 features
    
    som = CustomSOM(x_dim=2, y_dim=2, input_len=4)
    som.train(data, num_epochs=10)
    
    # Quantization error must be small
    qe = som.get_quantization_error(data)
    assert qe >= 0.0
    
    # Topographic error must be in [0, 1]
    te = som.get_topographic_error(data)
    assert 0.0 <= te <= 1.0
    
    # Check projection mapping
    coords = som.project(data)
    assert len(coords) == 10
    assert all(0 <= c[0] < 2 and 0 <= c[1] < 2 for c in coords)

def test_som_vulnerability_engine():
    topo = GridTopology()
    engine = SomVulnerabilityEngine(topo)
    
    # Test features generation
    bus_feats = engine.get_bus_features()
    line_feats = engine.get_line_features()
    
    assert bus_feats.shape[0] == 39
    assert line_feats.shape[0] == 46
    
    # Test clustering output structure
    res = engine.cluster_grid(2, 2, num_epochs=10)
    assert "bus_clusters" in res
    assert "line_clusters" in res
    assert "communities" in res
    
    assert len(res["bus_clusters"]) == 39
    assert len(res["line_clusters"]) == 46
    assert len(res["communities"]) == 4 # 2x2 grid = 4 clusters

def test_concurrent_attack_planner():
    topo = GridTopology()
    planner = ConcurrentAttackEngine(topo)
    
    # Test combination generation
    combos = planner.get_attack_combinations([1, 2, 3, 4], 2)
    assert len(combos) == 6
    assert (1, 2) in combos
    
    # Test planning on Community 0
    res = planner.plan_optimal_attack(community_id=0, num_targets=2, attack_type="TRIP_LINE")
    assert "targets" in res
    assert "score" in res
    assert "metrics" in res
    assert len(res["targets"]) <= 2

def test_imperfect_pathogen_env_concurrent_mode():
    # Test env execution under SEQUENTIAL vs CONCURRENT campaign modes
    env = ImperfectPathogenEnv(mode="B")
    
    # Reset
    obs, info = env.reset(seed=42)
    assert obs.shape == (293,)
    
    # Test SEQUENTIAL TRIP_LINE (trips 1 line)
    action_seq = {"type": 4, "target": 2, "magnitude": np.array([0.0], dtype=np.float32)}
    next_obs, reward, term, trunc, info = env.step(action_seq)
    # Target line index 2 corresponds to L_line_2
    assert env.breakers["L_line_2"] == "OPEN"
    
    # Test CONCURRENT campaign mode
    env.campaign_mode = "CONCURRENT"
    # Reset to nominal state
    env.reset(seed=42)
    assert env.breakers["L_line_2"] == "CLOSED"
    
    # Step with TRIP_LINE targeting target 2
    action_conc = {"type": 4, "target": 2, "magnitude": np.array([0.0], dtype=np.float32)}
    env.step(action_conc)
    
    # Concurrent campaign must trip multiple lines in the target's community simultaneously
    opened_breakers = [lid for lid, state in env.breakers.items() if state == "OPEN"]
    assert len(opened_breakers) >= 2 # Concurrent attack planned and tripped multiple lines
