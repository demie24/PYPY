import pytest
from core.assistant.distributed_consensus_engine import DistributedConsensusEngine

def test_consensus_engine_initial_state():
    engine = DistributedConsensusEngine()
    summary = engine.get_status_summary()
    assert summary["agent_name"] == "DistributedConsensusEngine"
    assert summary["status"] == "NOMINAL"
    assert summary["consensus_state"] == "IDLE"
    assert summary["consensus_score"] == 1.0
    assert summary["consensus_drift"] == 0.0

def test_consensus_engine_unanimous_approval():
    engine = DistributedConsensusEngine()
    votes = {
        "esp32_1": {"decision": "ISOLATE_ZONE_A", "confidence": 0.90},
        "esp32_2": {"decision": "ISOLATE_ZONE_A", "confidence": 0.95},
        "esp32_3": {"decision": "ISOLATE_ZONE_A", "confidence": 0.85},
        "plc_1": {"decision": "ISOLATE_ZONE_A", "confidence": 1.0},
        "plc_2": {"decision": "ISOLATE_ZONE_A", "confidence": 0.90}
    }
    
    summary = engine.arbitrate_consensus(votes)
    assert summary["consensus_state"] == "APPROVED"
    assert summary["consensus_score"] >= 0.85
    assert summary["status"] == "NOMINAL"

def test_consensus_engine_conflict_blocked():
    engine = DistributedConsensusEngine()
    # 50/50 split vote
    votes = {
        "esp32_1": {"decision": "ISOLATE_ZONE_A", "confidence": 0.90},
        "esp32_2": {"decision": "ISOLATE_ZONE_A", "confidence": 0.90},
        "esp32_3": {"decision": "KEEP_ONLINE", "confidence": 0.90},
        "plc_1": {"decision": "KEEP_ONLINE", "confidence": 0.90}
    }
    summary = engine.arbitrate_consensus(votes)
    assert summary["consensus_state"] == "BLOCKED (CONFLICT)"
    assert summary["status"] == "CRITICAL"

def test_consensus_engine_low_confidence():
    engine = DistributedConsensusEngine()
    votes = {
        "esp32_1": {"decision": "ISOLATE_ZONE_A", "confidence": 0.60},
        "esp32_2": {"decision": "ISOLATE_ZONE_A", "confidence": 0.70},
        "esp32_3": {"decision": "ISOLATE_ZONE_A", "confidence": 0.65},
        "plc_1": {"decision": "ISOLATE_ZONE_A", "confidence": 0.50}
    }
    summary = engine.arbitrate_consensus(votes)
    assert summary["consensus_state"] == "BLOCKED (LOW_CONFIDENCE)"
    assert summary["status"] == "DEGRADED"

def test_consensus_engine_simulation_instability():
    engine = DistributedConsensusEngine()
    summary = engine.arbitrate_consensus({}, simulation_mode="consensus_instability")
    assert summary["consensus_state"] == "BLOCKED (INSTABILITY)"
    assert summary["consensus_drift"] == 0.65
    
    summary_drift = engine.arbitrate_consensus({}, simulation_mode="distributed_drift_escalation")
    assert summary_drift["consensus_state"] == "BLOCKED (DRIFT)"
    assert summary_drift["consensus_drift"] == 0.85

def test_consensus_engine_reset():
    engine = DistributedConsensusEngine()
    votes = {"node": {"decision": "A", "confidence": 0.9}}
    engine.arbitrate_consensus(votes)
    engine.reset_engine()
    assert engine.consensus_state == "IDLE"
    assert not engine.votes
    assert not engine.drift_history
