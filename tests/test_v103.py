import os
import sys
import numpy as np
import pytest
import torch

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from core.gnn.telemetry_reconstruction_gnn import (
    GCNConvNative,
    GATConvNative,
    TelemetryReconstructionGAE,
    PinnPhysicsValidator,
    integrate_trust_reconstruction,
    virtualize_blue_observation
)
from core.gnn.missing_data_simulator import MissingDataSimulator
from core.digital_twin.grid_topology import GridTopology
from core.adversarial.mqtt_verification_worker import MqttVerificationWorker

def test_gcn_conv_native():
    in_features = 4
    out_features = 8
    num_nodes = 5
    batch_size = 2
    
    gcn = GCNConvNative(in_features, out_features)
    x = torch.randn(batch_size, num_nodes, in_features)
    norm_adj = torch.eye(num_nodes) # Identity adjacency
    
    out = gcn(x, norm_adj)
    
    assert out.shape == (batch_size, num_nodes, out_features)
    assert torch.all(out >= 0.0) # ReLU activation checks

def test_gat_conv_native():
    in_features = 4
    out_features = 8
    num_nodes = 5
    batch_size = 2
    
    gat = GATConvNative(in_features, out_features)
    x = torch.randn(batch_size, num_nodes, in_features)
    adj = torch.ones(num_nodes, num_nodes) # Fully connected adjacency
    
    out = gat(x, adj)
    
    assert out.shape == (batch_size, num_nodes, out_features)
    assert torch.all(out >= 0.0) # ReLU activation checks

def test_telemetry_reconstruction_gae():
    num_nodes = 39
    edge_index = [(i, (i + 1) % num_nodes) for i in range(num_nodes)] # cycle graph
    
    gae = TelemetryReconstructionGAE(edge_index=edge_index, num_nodes=num_nodes, in_features=4, hidden_dim=16)
    
    # 4 features: [P, Q, V, theta]
    x = torch.randn(2, num_nodes, 4)
    
    recon_nodes, node_std, recon_edges, edge_std = gae(x)
    
    assert recon_nodes.shape == (2, num_nodes, 4)
    assert node_std.shape == (2, num_nodes, 4)
    assert torch.all(node_std > 0)
    
    num_edges = len(edge_index)
    assert recon_edges.shape == (2, num_edges)
    assert edge_std.shape == (2, num_edges)
    assert torch.all(edge_std > 0)

def test_missing_data_simulator():
    sim = MissingDataSimulator(num_buses=39, num_lines=46)
    obs = np.ones(293, dtype=np.float32)
    obs[0:39] = 1.05 # Voltages
    obs[39:78] = 0.5 # Active Injections
    obs[78:124] = 0.8 # Loadings
    
    # 1. Random Sensor Failure
    masked_sf, mask_sf = sim.simulate_sensor_failure(obs, mask_ratio=0.20)
    assert masked_sf.shape == (293,)
    assert mask_sf.shape == (293,)
    # physical parameters are in 0:124
    num_dropped = np.sum(mask_sf[0:124])
    expected_dropped = int(124 * 0.20)
    assert num_dropped == expected_dropped
    
    # Check default/nominal overrides
    for i in range(124):
        if mask_sf[i]:
            if i < 39:
                assert masked_sf[i] == 1.0
            elif i < 78:
                assert masked_sf[i] == 0.0
            else:
                assert masked_sf[i] == 0.0
                
    # 2. Targeted DoS
    target_buses = {5, 25}
    masked_dos, mask_dos = sim.simulate_targeted_dos(obs, target_buses)
    for bus_id in target_buses:
        assert mask_dos[bus_id] == True
        assert masked_dos[bus_id] == 1.0
        assert mask_dos[39 + bus_id] == True
        assert masked_dos[39 + bus_id] == 0.0
        
    # 3. MQTT Packet Loss (Burst)
    masked_mqtt, mask_mqtt = sim.simulate_mqtt_packet_loss(obs, burst_length=10)
    # Total masked must be exactly 10 in physical dims
    assert np.sum(mask_mqtt[0:124]) == 10
    
    # Ensure consecutive
    masked_indices = np.where(mask_mqtt)[0]
    assert len(masked_indices) == 10
    assert masked_indices[-1] - masked_indices[0] == 9
    
    # 4. Quarantine
    masked_q, mask_q = sim.simulate_quarantine(obs, quarantined_buses={12})
    assert mask_q[12] == True
    assert masked_q[12] == 1.0
    assert mask_q[39 + 12] == True
    assert masked_q[39 + 12] == 0.0

def test_pinn_physics_validator():
    topo = GridTopology()
    validator = PinnPhysicsValidator(topo)
    
    # Construct nominal telemetry
    V = np.ones(39, dtype=np.float32)
    theta = np.zeros(39, dtype=np.float32)
    P = np.zeros(39, dtype=np.float32)
    Q = np.zeros(39, dtype=np.float32)
    
    is_valid, residuals = validator.validate(V, theta, P, Q)
    assert isinstance(is_valid, bool)
    assert residuals.shape == (39,)

def test_trust_fusion_integration():
    worker = MqttVerificationWorker()
    bus_id = 25
    
    # Default trust is 1.0 (or set on first access)
    t1 = integrate_trust_reconstruction(worker, bus_id, confidence_score=0.95)
    assert t1 == 1.0 # default trust + 0.02 capped at 1.0
    
    # Artificially set trust to 0.5
    worker.bus_states[bus_id]["trust_score"] = 0.5
    
    # Test trust recovery with high confidence
    t2 = integrate_trust_reconstruction(worker, bus_id, confidence_score=0.92)
    assert abs(t2 - 0.52) < 1e-5
    
    # Test trust penalty with low confidence
    t3 = integrate_trust_reconstruction(worker, bus_id, confidence_score=0.45)
    assert abs(t3 - 0.47) < 1e-5
    
    # Test boundaries (capped at 0.0 and 1.0)
    worker.bus_states[bus_id]["trust_score"] = 0.02
    t4 = integrate_trust_reconstruction(worker, bus_id, confidence_score=0.30)
    assert t4 == 0.0
    
    worker.bus_states[bus_id]["trust_score"] = 0.99
    t5 = integrate_trust_reconstruction(worker, bus_id, confidence_score=0.98)
    assert t5 == 1.0

def test_blue_agent_virtualization():
    obs = np.ones(293, dtype=np.float32)
    reconstructed = np.zeros(124, dtype=np.float32)
    reconstructed[0:39] = 1.05
    reconstructed[39:78] = 0.25
    reconstructed[78:124] = 0.45
    
    missing_mask = np.zeros(293, dtype=bool)
    missing_mask[5] = True # missing voltage
    missing_mask[39 + 10] = True # missing injection
    missing_mask[78 + 3] = True # missing loading
    
    clean_obs = virtualize_blue_observation(obs, reconstructed, missing_mask)
    
    assert clean_obs[5] == 1.05
    assert clean_obs[39 + 10] == 0.25
    assert clean_obs[78 + 3] == 0.45
    
    # Other components should remain unchanged
    assert clean_obs[0] == 1.0
    assert clean_obs[39 + 0] == 1.0
    assert clean_obs[78 + 0] == 1.0
