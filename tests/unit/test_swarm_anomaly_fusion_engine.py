import pytest
from core.assistant.swarm_anomaly_fusion_engine import SwarmAnomalyFusionEngine

def test_anomaly_fusion_initial_state():
    engine = SwarmAnomalyFusionEngine()
    summary = engine.get_status_summary()
    assert summary["agent_name"] == "SwarmAnomalyFusionEngine"
    assert summary["status"] == "NOMINAL"
    assert summary["swarm_threat_score"] == 0.0
    assert not summary["fused_anomalies"]
    assert not summary["priority_queue"]

def test_anomaly_fusion_combining_findings():
    engine = SwarmAnomalyFusionEngine()
    
    telemetry_anoms = [{"variable": "bus_1_v", "severity": "HIGH", "confidence": 0.80, "description": "Voltan rendah"}]
    relay_anoms = [{"description": "Breaker chattering", "severity": "MEDIUM", "confidence": 0.70}]
    security_alerts = [{"type": "FDIA", "severity": "CRITICAL", "confidence": 0.90, "description": "Modbus injection"}]
    edge_anoms = {"esp32_zone3": ["OFFLINE"]}

    summary = engine.fuse_anomalies(telemetry_anoms, relay_anoms, security_alerts, edge_anoms)
    
    # We should have 4 fused anomalies
    assert len(summary["fused_anomalies"]) == 4
    
    # Priority Queue should sort CRITICAL (Security & Edge offline) first
    assert len(summary["priority_queue"]) == 4
    assert summary["priority_queue"][0]["severity"] == "CRITICAL"
    assert summary["priority_queue"][-1]["severity"] == "MEDIUM"
    
    # Threat score should be > 0.0
    assert summary["swarm_threat_score"] > 2.0
    assert summary["status"] == "CRITICAL" # weighted threat score escalates status

def test_anomaly_fusion_correlation_matrix():
    engine = SwarmAnomalyFusionEngine()
    # Active sources: telemetry, security
    engine.fuse_anomalies(
        telemetry_anoms=[{"severity": "MEDIUM", "confidence": 0.7}],
        relay_anoms=[],
        security_alerts=[{"severity": "HIGH", "confidence": 0.8}],
        edge_anoms={}
    )
    
    matrix = engine.correlation_matrix
    # Both active -> high correlation
    assert matrix["telemetry"]["security"] == 0.85
    # One active, one inactive -> baseline correlation
    assert matrix["telemetry"]["relay"] == 0.15

def test_anomaly_fusion_simulation_overload():
    engine = SwarmAnomalyFusionEngine()
    summary = engine.fuse_anomalies([], [], [], {}, simulation_mode="anomaly_fusion_overload")
    assert summary["swarm_threat_score"] == 9.8
    assert summary["status"] == "CRITICAL"
    assert len(summary["fused_anomalies"]) == 1
    assert summary["fused_anomalies"][0]["source"] == "FUSION_OVERLOAD"

def test_anomaly_fusion_reset():
    engine = SwarmAnomalyFusionEngine()
    engine.fuse_anomalies([{"severity": "HIGH", "confidence": 0.8}], [], [], {})
    engine.reset_engine()
    assert engine.swarm_threat_score == 0.0
    assert not engine.fused_anomalies
    assert not engine.priority_queue
    assert not engine.correlation_matrix
