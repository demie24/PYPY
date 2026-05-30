import pytest
from core.assistant.edge_mesh_orchestrator import EdgeMeshOrchestrator

def test_edge_mesh_initial_state():
    orch = EdgeMeshOrchestrator()
    summary = orch.get_status_summary()
    assert summary["agent_name"] == "EdgeMeshOrchestrator"
    assert summary["status"] == "NOMINAL"
    assert summary["mesh_status"] == "CONNECTED"
    assert not summary["links"]
    assert not summary["partition_failures"]

def test_edge_mesh_tick_nominal():
    orch = EdgeMeshOrchestrator()
    edge_summary = {
        "nodes": {
            "esp32_zone1": {"online": True, "health": 1.0, "latency_ms": 45.0},
            "esp32_zone2": {"online": True, "health": 1.0, "latency_ms": 45.0},
            "esp32_zone3": {"online": True, "health": 1.0, "latency_ms": 45.0},
            "plc_primary": {"online": True, "health": 1.0, "latency_ms": 12.0},
            "plc_backup": {"online": True, "health": 1.0, "latency_ms": 12.0},
            "esp32_backup": {"online": True, "health": 1.0, "latency_ms": 45.0}
        }
    }
    summary = orch.tick_mesh_orchestrator(edge_summary, {})
    assert summary["mesh_status"] == "CONNECTED"
    assert len(summary["links"]) > 0
    # Every link should be active since all nodes are online
    assert all(l["status"] == "ACTIVE" for l in summary["links"])

def test_edge_mesh_partition_simulation():
    orch = EdgeMeshOrchestrator()
    edge_summary = {
        "nodes": {
            "esp32_zone1": {"online": True, "health": 1.0},
            "esp32_zone2": {"online": True, "health": 1.0},
            "esp32_zone3": {"online": True, "health": 1.0},
            "plc_primary": {"online": True, "health": 1.0},
            "plc_backup": {"online": True, "health": 1.0},
            "esp32_backup": {"online": True, "health": 1.0}
        }
    }
    
    # Trigger partition simulation
    summary = orch.tick_mesh_orchestrator(edge_summary, {}, simulation_mode="edge_mesh_partition_failures")
    assert summary["mesh_status"] == "PARTITIONED"
    assert summary["status"] == "CRITICAL"
    assert len(summary["partition_failures"]) == 1
    
    # Locate the broken link (esp32_zone2 <-> esp32_zone3)
    broken_links = [l for l in summary["links"] if l["status"] == "BROKEN"]
    assert len(broken_links) == 1
    pair = {broken_links[0]["source"], broken_links[0]["target"]}
    assert "esp32_zone2" in pair and "esp32_zone3" in pair

def test_edge_mesh_cascade_risk_path():
    orch = EdgeMeshOrchestrator()
    # esp32_zone1 health degraded to 0.45
    edge_summary = {
        "nodes": {
            "esp32_zone1": {"online": True, "health": 0.45, "latency_ms": 45.0},
            "esp32_zone2": {"online": True, "health": 1.0, "latency_ms": 45.0},
            "esp32_zone3": {"online": True, "health": 1.0, "latency_ms": 45.0},
            "plc_primary": {"online": True, "health": 1.0, "latency_ms": 12.0},
            "plc_backup": {"online": True, "health": 1.0, "latency_ms": 12.0},
            "esp32_backup": {"online": True, "health": 1.0, "latency_ms": 45.0}
        }
    }
    summary = orch.tick_mesh_orchestrator(edge_summary, {})
    # Active links connected to esp32_zone1 are at risk of cascading degradation
    assert len(summary["cascade_risk_paths"]) > 0
    # Paths should involve esp32_zone1
    assert any("esp32_zone1" in p["path"] for p in summary["cascade_risk_paths"])

def test_edge_mesh_reset():
    orch = EdgeMeshOrchestrator()
    orch.tick_mesh_orchestrator({"nodes": {"esp32_zone1": {"online": False}}}, {}, "edge_mesh_partition_failures")
    orch.reset_orchestrator()
    assert orch.mesh_status == "CONNECTED"
    assert not orch.links
    assert not orch.partition_failures
