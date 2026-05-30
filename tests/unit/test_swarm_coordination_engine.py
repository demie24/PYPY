import pytest
from core.assistant.federated_memory_manager import FederatedMemoryManager
from core.assistant.distributed_consensus_engine import DistributedConsensusEngine
from core.assistant.edge_mesh_orchestrator import EdgeMeshOrchestrator
from core.assistant.swarm_anomaly_fusion_engine import SwarmAnomalyFusionEngine
from core.assistant.swarm_coordination_engine import SwarmCoordinationEngine

@pytest.fixture
def swarm_setup():
    fed_mem = FederatedMemoryManager()
    dist_con = DistributedConsensusEngine()
    mesh = EdgeMeshOrchestrator()
    fusion = SwarmAnomalyFusionEngine()
    coord = SwarmCoordinationEngine(fed_mem, dist_con, mesh, fusion)
    return coord, fed_mem, dist_con, mesh, fusion

def test_swarm_coordinator_initial_state(swarm_setup):
    coord, _, _, _, _ = swarm_setup
    summary = coord.get_status_summary()
    assert summary["agent_name"] == "SwarmCoordinationEngine"
    assert summary["status"] == "NOMINAL"
    assert not summary["coordination_chain"]
    assert not summary["coordination_logs"]

def test_swarm_coordinator_nominal_tick(swarm_setup):
    coord, _, _, _, _ = swarm_setup
    telemetry = {"bus_1_v": 1.0}
    sync_states = {"node_sync_states": {}}
    edge_summary = {"nodes": {}, "anomalies": {}}
    relay_summary = {"anomalies": []}
    security_summary = {"threat_alerts": []}
    
    summary = coord.coordinate_swarm(telemetry, sync_states, edge_summary, relay_summary, security_summary, [])
    assert summary["status"] == "NOMINAL"
    assert len(summary["coordination_chain"]) == 1 # only edge mesh checked since threat is 0

def test_swarm_coordinator_loop_prevention(swarm_setup):
    coord, _, _, _, _ = swarm_setup
    telemetry = {}
    sync_states = {"node_sync_states": {}}
    edge_summary = {"nodes": {}, "anomalies": {}}
    relay_summary = {"anomalies": []}
    security_summary = {"threat_alerts": []}
    
    # Trigger recursion simulation
    coord.simulation_mode = "distributed_drift_escalation"
    summary = coord.coordinate_swarm(telemetry, sync_states, edge_summary, relay_summary, security_summary, [])
    assert summary["status"] == "LOOP_PREVENTED"
    assert "LOOP_PREVENTED" in coord.status
    assert coord.distributed_consensus.consensus_state == "BLOCKED (LOOP_PREVENTED)"
    assert coord.distributed_consensus.consensus_score == 0.0

def test_swarm_coordinator_query_intercepts(swarm_setup):
    coord, fed_mem, dist_con, mesh, fusion = swarm_setup
    
    # Setup some state for replies
    dist_con.consensus_state = "APPROVED"
    dist_con.consensus_score = 0.85
    dist_con.votes = {
        "n1": {"decision": "ISOLATE_ZONE_A", "confidence": 0.85},
        "n2": {"decision": "ISOLATE_ZONE_A", "confidence": 0.85}
    }
    mesh.nodes["esp32_zone3"]["online"] = False
    
    # 1. "swarm consensus report"
    res1 = coord.handle_query("Laporan konsensus swarm?")
    assert "APPROVED" in res1
    assert "0.85" in res1
    
    # 2. "node mana paling kritikal dalam mesh"
    # Mock worst node
    mesh.status = "DEGRADED"
    # Force a tick to populate edgeMesh worst node pointers
    edge_summary = {
        "nodes": {
            "esp32_zone1": {"online": True, "health": 1.0},
            "esp32_zone2": {"online": True, "health": 1.0},
            "esp32_zone3": {"online": False, "health": 0.0},
            "plc_primary": {"online": True, "health": 1.0},
            "plc_backup": {"online": True, "health": 1.0},
            "esp32_backup": {"online": True, "health": 1.0}
        },
        "worst_node": "esp32_zone3"
    }
    mesh.tick_mesh_orchestrator(edge_summary, {})
    res2 = coord.handle_query("node mana paling kritikal dalam mesh")
    assert "esp32_zone3" in res2
    
    # 3. "gabungkan semua anomaly findings"
    fusion.fuse_anomalies([{"severity": "CRITICAL", "confidence": 0.90}], [], [], {})
    res3 = coord.handle_query("gabungkan semua anomaly findings")
    assert "Anomaly Fusion" in res3
    
    # 4. "buat distributed recovery coordination"
    res4 = coord.handle_query("buat distributed recovery coordination")
    assert "Konsensus DIPERSETUJUI" in res4
    assert "ISOLATE_ZONE_A" in res4
    
    # 5. "berapa confidence swarm sekarang"
    res5 = coord.handle_query("berapa confidence swarm sekarang")
    assert "semasa swarm ialah 0.85" in res5
