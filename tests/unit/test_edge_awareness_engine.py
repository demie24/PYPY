import pytest
from core.assistant.edge_awareness_engine import EdgeAwarenessEngine

def test_edge_awareness_engine_initialization():
    engine = EdgeAwarenessEngine()
    assert "esp32_zone1" in engine.nodes
    assert engine.nodes["esp32_zone1"]["health"] == 1.0
    assert engine.nodes["plc_primary"]["online"] is True
    assert not engine.anomalies

def test_update_edge_state_and_health():
    engine = EdgeAwarenessEngine()
    
    # 1. Update node within healthy bounds
    engine.update_edge_state("esp32_zone1", latency=45.0, packet_loss=0.0, online=True, drift_sec=0.01)
    assert engine.nodes["esp32_zone1"]["health"] == 1.0
    assert "esp32_zone1" not in engine.anomalies

    # 2. Latency penalty (starts > 100ms)
    # 100 + 400 = 500ms should deduct 1.0 health, max penalty is 0.4
    engine.update_edge_state("esp32_zone1", latency=180.0, packet_loss=0.0, online=True, drift_sec=0.0)
    health_score = engine.nodes["esp32_zone1"]["health"]
    assert health_score < 1.0
    assert "esp32_zone1" in engine.anomalies
    assert "HIGH_LATENCY" in engine.anomalies["esp32_zone1"]

    # 3. Packet loss penalty
    # 10% packet loss should deduct 0.10, max is 0.35
    engine.update_edge_state("esp32_zone1", latency=40.0, packet_loss=10.0, online=True, drift_sec=0.0)
    health_score = engine.nodes["esp32_zone1"]["health"]
    assert abs(health_score - 0.90) < 0.001
    assert "PACKET_LOSS_DETECTION" in engine.anomalies["esp32_zone1"]

    # 4. Clock drift penalty (> 0.02s)
    # 0.06 drift should deduct (0.06 - 0.02) * 5.0 = 0.20, max is 0.25
    engine.update_edge_state("esp32_zone1", latency=40.0, packet_loss=0.0, online=True, drift_sec=0.06)
    health_score = engine.nodes["esp32_zone1"]["health"]
    assert abs(health_score - 0.80) < 0.001
    assert "SYNC_DRIFT_SKEW" in engine.anomalies["esp32_zone1"]

    # 5. Offline state
    engine.update_edge_state("esp32_zone1", latency=None, packet_loss=None, online=False, drift_sec=0.0)
    assert engine.nodes["esp32_zone1"]["health"] == 0.0
    assert "OFFLINE" in engine.anomalies["esp32_zone1"]

def test_get_worst_node_and_tie_breaker():
    engine = EdgeAwarenessEngine()
    
    # Set one node degraded
    engine.update_edge_state("esp32_zone1", latency=300.0, packet_loss=0.0, online=True) # health = 0.5
    engine.update_edge_state("esp32_zone2", latency=45.0, packet_loss=0.0, online=True)  # health = 1.0
    assert engine.get_worst_node() == "esp32_zone1"

    # Set tie-breaker: esp32_zone2 has same health deduction but higher latency/drift
    engine.update_edge_state("esp32_zone1", latency=300.0, packet_loss=0.0, online=True)
    engine.update_edge_state("esp32_zone2", latency=350.0, packet_loss=0.0, online=True)
    # tie breaker logic should select the one with higher latency
    assert engine.get_worst_node() == "esp32_zone2"

def test_get_status_summary():
    engine = EdgeAwarenessEngine()
    engine.update_edge_state("esp32_zone1", latency=200.0, packet_loss=10.0, online=True, drift_sec=0.06)
    summary = engine.get_status_summary()
    assert summary["worst_node"] == "esp32_zone1"
    assert summary["distributed_anomaly_count"] == 1
    assert summary["average_latency_ms"] > 0

def test_reset_engine():
    engine = EdgeAwarenessEngine()
    engine.update_edge_state("esp32_zone1", latency=300.0, packet_loss=15.0, online=False, drift_sec=0.1)
    engine.reset_engine()
    assert engine.nodes["esp32_zone1"]["health"] == 1.0
    assert not engine.anomalies
