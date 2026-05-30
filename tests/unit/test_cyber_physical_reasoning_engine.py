import pytest
from core.assistant.cyber_physical_reasoning_engine import CyberPhysicalReasoningEngine

def test_cyber_physical_reasoning_engine_initialization():
    engine = CyberPhysicalReasoningEngine()
    assert engine.severity_score == 0.0
    assert engine.severity_level == "LOW"
    assert not engine.suggestions
    assert not engine.reasoning_logs

def test_evaluate_state_severity_fusing():
    engine = CyberPhysicalReasoningEngine()
    
    # Mock summaries
    edge_sum = {"worst_node_health": 0.8}    # edge penalty: (1 - 0.8) * 30 = 6.0
    relay_sum = {"unstable_count": 1, "breakers": {}}        # relay penalty: 1 * 20 = 20.0
    correlation_sum = {"cascades": []}        # corr penalty: 0
    sync_sum = {"skewed_count": 2, "skewed_nodes": []}       # sync penalty: 2 * 10 = 20.0
    
    res = engine.evaluate_state(
        edge_sum=edge_sum,
        relay_sum=relay_sum,
        correlation_sum=correlation_sum,
        sync_sum=sync_sum,
        threat_score=40.0,                    # base threat comp: 40 * 0.3 = 12.0
        threat_confidence=1.0
    )
    
    expected_score = 6.0 + 20.0 + 0.0 + 20.0 + 12.0 # 58.0
    assert abs(res["severity_score"] - expected_score) < 0.001
    assert res["severity_level"] == "HIGH" # 50.0 to 75.0 is HIGH
    assert len(res["reasoning_logs"]) > 0

def test_evaluate_state_recommendations():
    engine = CyberPhysicalReasoningEngine()
    
    edge_sum = {"worst_node_health": 1.0}
    relay_sum = {
        "unstable_count": 1,
        "breakers": {
            "L1_4": {"unstable": True}
        }
    }
    correlation_sum = {
        "cascades": [
            {"cause": "breaker_1_OPEN", "effect": "bus_2_v_UNDERVOLTAGE"}
        ]
    }
    sync_sum = {
        "skewed_count": 1,
        "skewed_nodes": ["esp32_zone1"]
    }
    
    # 1. Threat confidence high (>= 0.75) -> allows actions
    res = engine.evaluate_state(
        edge_sum=edge_sum,
        relay_sum=relay_sum,
        correlation_sum=correlation_sum,
        sync_sum=sync_sum,
        threat_score=100.0, # critical
        threat_confidence=0.85
    )
    
    actions = [s["action"] for s in res["suggestions"]]
    assert "LOCKOUT_BREAKER" in actions
    assert "SYNC_RECOVERY" in actions
    assert "ISOLATE_PROPAGATION_PATH" in actions
    assert "OPERATOR_ESCALATION" in actions # because severity is CRITICAL

    # 2. Threat confidence low (< 0.75) -> safety gates/blocks suggestions
    res = engine.evaluate_state(
        edge_sum=edge_sum,
        relay_sum=relay_sum,
        correlation_sum=correlation_sum,
        sync_sum=sync_sum,
        threat_score=100.0,
        threat_confidence=0.60
    )
    actions = [s["action"] for s in res["suggestions"]]
    assert "OPERATOR_VERIFICATION" in actions
    assert "MONITOR_TIMING" in actions
    assert "LOCKOUT_BREAKER" not in actions
    assert "SYNC_RECOVERY" not in actions

def test_handle_query_in_malay():
    engine = CyberPhysicalReasoningEngine()
    
    # Mock profiles
    edge_sum = {
        "worst_node": "esp32_zone1",
        "worst_node_health": 0.85,
        "nodes": {
            "esp32_zone1": {"latency_ms": 160.0, "drift_sec": 0.035, "health": 0.85}
        }
    }
    relay_sum = {
        "unstable_breakers": ["L1_4"],
        "breakers": {
            "L1_4": {"unstable": True, "wear_pct": 82.0}
        },
        "wear_report": {"L1_4": 82.0}
    }
    correlation_sum = {
        "cascades": [{"cause": "breaker_1_OPEN", "effect": "bus_2_v_UNDERVOLTAGE"}]
    }
    sync_sum = {
        "max_drift_node": "esp32_zone1",
        "max_drift_ms": 35.0,
        "skewed_nodes": ["esp32_zone1"]
    }
    
    # 1. Ask about node problems
    ans = engine.handle_query("node mana paling bermasalah sekarang?", edge_sum, relay_sum, correlation_sum, sync_sum)
    assert ans is not None
    assert "esp32_zone1" in ans
    assert "health index 0.85" in ans
    
    # 2. Ask about unstable/oscillation breaker
    ans = engine.handle_query("ada tak breaker unstable atau oscillation?", edge_sum, relay_sum, correlation_sum, sync_sum)
    assert ans is not None
    assert "L1_4" in ans
    assert "oscillation" in ans
    
    # 3. Ask about clock sync/drift
    ans = engine.handle_query("macam mana dengan synchronization delay?", edge_sum, relay_sum, correlation_sum, sync_sum)
    assert ans is not None
    assert "esp32_zone1" in ans
    assert "drift delay" in ans or "drift" in ans

    # 4. Ask about stabilization workflow
    # High confidence -> yields workflow
    ans = engine.handle_query("cadangkan stabilization workflow", edge_sum, relay_sum, correlation_sum, sync_sum, threat_confidence=0.8)
    assert ans is not None
    assert "Lockout breaker L1_4" in ans
    assert "PTP Timing Recalibration" in ans

    # Low confidence -> workflow blocked
    ans = engine.handle_query("cadangkan stabilization workflow", edge_sum, relay_sum, correlation_sum, sync_sum, threat_confidence=0.5)
    assert ans is not None
    assert "disekat" in ans
