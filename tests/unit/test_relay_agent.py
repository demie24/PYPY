import pytest
from core.assistant.relay_agent import RelayAgent

def test_relay_agent_initial_state():
    agent = RelayAgent()
    summary = agent.get_status_summary()
    assert summary["agent_name"] == "RelayAgent"
    assert summary["status"] == "NOMINAL"
    assert summary["confidence_score"] == 1.0
    assert not summary["anomalies"]
    assert not summary["recommendations"]
    assert not summary["coordination_support_needed"]

def test_relay_agent_wear_tear():
    agent = RelayAgent()
    health_summary = {
        "breakers": {
            "L1_4": {"wear_pct": 55.0, "timing_ms": 50.0, "unstable": False},
            "L2_3": {"wear_pct": 85.0, "timing_ms": 50.0, "unstable": False}
        }
    }
    agent.analyze_relays(health_summary)
    assert agent.status == "HIGH_ANOMALY"
    assert len(agent.relay_anomalies) == 2
    
    # 85% wear is HIGH severity, 55% wear is MEDIUM severity
    anoms = sorted(agent.relay_anomalies, key=lambda x: x["breaker"])
    assert anoms[0]["breaker"] == "L1_4"
    assert anoms[0]["severity"] == "MEDIUM"
    assert anoms[1]["breaker"] == "L2_3"
    assert anoms[1]["severity"] == "HIGH"
    
    # Check recommendation for high wear
    recs = agent.stabilization_recommendations
    assert len(recs) == 1
    assert recs[0]["action"] == "REPLACE_CONTACT"
    assert recs[0]["target"] == "L2_3"
    assert "ganti physical contact" in recs[0]["suggestion"]

def test_relay_agent_slow_breaker():
    agent = RelayAgent()
    health_summary = {
        "breakers": {
            "L3_6": {"wear_pct": 10.0, "timing_ms": 130.0, "unstable": False}
        }
    }
    agent.analyze_relays(health_summary)
    assert agent.status == "HIGH_ANOMALY"
    assert len(agent.relay_anomalies) == 1
    assert agent.relay_anomalies[0]["metric"] == "TIMING"
    assert agent.relay_anomalies[0]["severity"] == "HIGH"
    
    # Check recommendation for slow timing
    recs = agent.stabilization_recommendations
    assert len(recs) == 1
    assert recs[0]["action"] == "CALIBRATE_SOLENOID"
    assert "timing calibration" in recs[0]["suggestion"]

def test_relay_agent_breaker_oscillation():
    agent = RelayAgent()
    health_summary = {
        "breakers": {
            "L3_6": {"wear_pct": 20.0, "timing_ms": 50.0, "unstable": True}
        }
    }
    agent.analyze_relays(health_summary)
    assert agent.status == "CRITICAL_ANOMALY"
    assert len(agent.relay_anomalies) == 1
    assert agent.relay_anomalies[0]["metric"] == "OSCILLATION"
    assert agent.relay_anomalies[0]["severity"] == "CRITICAL"
    
    # Check recommendation
    recs = agent.stabilization_recommendations
    assert len(recs) == 1
    assert recs[0]["action"] == "LOCKOUT_BREAKER"
    assert "lockout keselamatan segera" in recs[0]["suggestion"]

def test_relay_agent_safety_confidence_gate():
    agent = RelayAgent()
    health_summary = {
        "breakers": {
            "L3_6": {"wear_pct": 20.0, "timing_ms": 50.0, "unstable": True}
        }
    }
    
    # Test blocked due to low confidence (< 0.75)
    agent.analyze_relays(health_summary, global_confidence=0.70)
    assert len(agent.stabilization_recommendations) == 1
    assert agent.stabilization_recommendations[0]["blocked"] is True
    assert "disekat" in agent.stabilization_recommendations[0]["suggestion"]
    
    # Test allowed/approved with high confidence (>= 0.75)
    agent.analyze_relays(health_summary, global_confidence=0.80)
    assert len(agent.stabilization_recommendations) == 1
    assert agent.stabilization_recommendations[0]["blocked"] is False
    assert "lockout keselamatan segera" in agent.stabilization_recommendations[0]["suggestion"]

def test_relay_agent_reset():
    agent = RelayAgent()
    health_summary = {
        "breakers": {
            "L3_6": {"wear_pct": 20.0, "timing_ms": 50.0, "unstable": True}
        }
    }
    agent.analyze_relays(health_summary)
    assert agent.status == "CRITICAL_ANOMALY"
    
    agent.reset_agent()
    assert agent.status == "NOMINAL"
    assert not agent.relay_anomalies
    assert not agent.stabilization_recommendations
