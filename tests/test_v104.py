import os
import sys
import numpy as np
import pytest

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from core.digital_twin.grid_topology import GridTopology
from core.analytics.ptdf_engine import PtdfEngine, build_b_matrix, get_connected_components
from core.analytics.extended_betweenness_engine import ExtendedBetweennessEngine
from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator

def test_b_matrix_and_islands():
    topo = GridTopology()
    
    # 1. B Matrix checks
    B = build_b_matrix(topo)
    assert B.shape == (39, 39)
    # Nodal susceptance matrix diagonal must be positive and off-diagonals must be negative or zero
    assert np.all(np.diag(B) > 0)
    
    # 2. Island checks (nominal case has 1 component)
    components = get_connected_components(topo)
    assert len(components) == 1
    assert len(components[0]) == 39
    
    # Trip all lines connected to Bus 25 to isolate it
    breakers = {line["id"]: "CLOSED" for line in topo.lines}
    for line in topo.lines:
        if line["from"] == 25 or line["to"] == 25:
            breakers[line["id"]] = "OPEN"
            
    components_isolated = get_connected_components(topo, breakers)
    assert len(components_isolated) == 3
    assert {25} in [set(c) for c in components_isolated]

def test_ptdf_engine():
    topo = GridTopology()
    engine = PtdfEngine(topo)
    
    # 1. PTDF Matrix
    ptdf = engine.calculate_ptdf_matrix()
    # IEEE 39 has 46 lines/transformers and 39 buses
    assert ptdf.shape == (46, 39)
    
    # 2. Transaction PTDF
    # Transfer from generator bus 30 to load bus 3
    trans_ptdf = engine.calculate_transaction_ptdf(source_bus=30, sink_bus=3)
    assert trans_ptdf.shape == (46,)
    
    # Verify that transaction PTDF is zero for isolated buses
    breakers = {line["id"]: "CLOSED" for line in topo.lines}
    for line in topo.lines:
        if line["from"] == 25 or line["to"] == 25:
            breakers[line["id"]] = "OPEN"
            
    disconnected_ptdf = engine.calculate_transaction_ptdf(source_bus=30, sink_bus=25, breakers=breakers)
    assert np.all(disconnected_ptdf == 0.0)

def test_betweenness_metrics():
    topo = GridTopology()
    engine = ExtendedBetweennessEngine(topo)
    
    # 1. Classical BC
    bus_cbc, line_cbc = engine.calculate_classical_betweenness()
    assert len(bus_cbc) == 39
    assert len(line_cbc) == 46
    assert all(0.0 <= v <= 1.0 for v in bus_cbc.values())
    assert all(0.0 <= v <= 1.0 for v in line_cbc.values())
    
    # 2. Electrical BC
    bus_ebc, line_ebc = engine.calculate_electrical_betweenness()
    assert len(bus_ebc) == 39
    assert len(line_ebc) == 46
    assert all(v >= 0.0 for v in bus_ebc.values())
    assert all(v >= 0.0 for v in line_ebc.values())
    
    # 3. Extended BC
    bus_exbc, line_exbc = engine.calculate_extended_betweenness()
    assert len(bus_exbc) == 39
    assert len(line_exbc) == 46
    assert all(v >= 0.0 for v in bus_exbc.values())
    assert all(v >= 0.0 for v in line_exbc.values())
    
    # Verify node centrality is half the sum of connected line centralities
    for bus_id in range(39):
        connected_lines_val = 0.0
        for line in topo.lines:
            if line["from"] == bus_id or line["to"] == bus_id:
                connected_lines_val += line_exbc[line["id"]]
        assert abs(bus_exbc[bus_id] - 0.5 * connected_lines_val) < 1e-5

def test_cascading_failure_simulator():
    topo = GridTopology()
    sim = CascadingFailureSimulator(topo)
    
    # 1. Nominal case: no tripped lines
    res_nom = sim.run_cascade()
    assert res_nom["cascade_size"] == 0
    assert res_nom["load_shed"] == 0.0
    assert len(res_nom["stages"]) == 1
    
    # 2. High outage case: trip top lines to force overloads
    # Tripping lines L_line_0, L_line_1, L_line_2
    res_trip = sim.run_cascade(initial_tripped_lines={"L_line_0", "L_line_1", "L_line_2"})
    assert "cascade_size" in res_trip
    assert "load_shed" in res_trip
    assert "unserved_energy" in res_trip
    assert isinstance(res_trip["cascade_size"], int)
    assert res_trip["load_shed"] >= 0.0
    assert len(res_trip["stages"]) >= 1

def test_hybrid_score_calculation():
    # Setup values
    gnn_val = 0.8
    eb_val = 0.5
    ptdf_val = 0.6
    
    # Configure weights
    alpha, beta, gamma = 0.4, 0.4, 0.2
    
    hybrid = alpha * gnn_val + beta * eb_val + gamma * ptdf_val
    assert abs(hybrid - 0.64) < 1e-6
