import pytest
from core.assistant.security_agent import SecurityAgent

def test_security_agent_initial_state():
    agent = SecurityAgent()
    summary = agent.get_status_summary()
    assert summary["agent_name"] == "SecurityAgent"
    assert summary["status"] == "NOMINAL"
    assert summary["confidence_score"] == 1.0
    assert not summary["threat_alerts"]
    assert not summary["recommendations"]
    assert not summary["security_logs"]

def test_security_agent_threat_score():
    agent = SecurityAgent()
    # Test nominal
    agent.analyze_security({"threat_score": 15.0, "confidence": 1.0, "severity": "LOW"}, [])
    assert agent.status == "NOMINAL"
    
    # Test warning (>30%)
    agent.analyze_security({"threat_score": 45.0, "confidence": 0.90, "severity": "HIGH"}, [])
    assert agent.status == "HIGH_ANOMALY"
    assert len(agent.threat_alerts) == 1
    assert agent.threat_alerts[0]["type"] == "CYBER_THREAT_WARNING"
    
    # Test critical (>70%)
    agent.analyze_security({"threat_score": 85.0, "confidence": 0.95, "severity": "CRITICAL"}, [])
    assert agent.status == "CRITICAL_ANOMALY"
    assert len(agent.threat_alerts) == 1
    assert any(x["type"] == "CYBER_THREAT_CRITICAL" for x in agent.threat_alerts)

def test_security_agent_active_attacks():
    agent = SecurityAgent()
    agent.analyze_security({"threat_score": 10.0, "confidence": 1.0, "severity": "LOW"}, ["mitm_replay"])
    assert agent.status == "CRITICAL_ANOMALY"
    assert len(agent.threat_alerts) == 1
    assert agent.threat_alerts[0]["type"] == "ACTIVE_ATTACK"
    assert agent.threat_alerts[0]["attack"] == "mitm_replay"

def test_security_agent_quarantine_confidence_gate():
    agent = SecurityAgent()
    
    # Blocked due to low confidence (< 0.75)
    agent.analyze_security({"threat_score": 10.0, "confidence": 0.70, "severity": "LOW"}, ["replay"])
    assert len(agent.safety_recommendations) == 1
    assert agent.safety_recommendations[0]["action"] == "QUARANTINE_NODE"
    assert agent.safety_recommendations[0]["blocked"] is True
    assert "disekat" in agent.safety_recommendations[0]["suggestion"]
    
    # Allowed with high confidence (>= 0.75)
    agent.analyze_security({"threat_score": 10.0, "confidence": 0.85, "severity": "LOW"}, ["replay"])
    assert len(agent.safety_recommendations) == 1
    assert agent.safety_recommendations[0]["action"] == "QUARANTINE_NODE"
    assert agent.safety_recommendations[0]["blocked"] is False
    assert "Kuarantin" in agent.safety_recommendations[0]["suggestion"]

def test_security_agent_reset():
    agent = SecurityAgent()
    agent.analyze_security({"threat_score": 10.0, "confidence": 1.0, "severity": "LOW"}, ["replay"])
    assert agent.status == "CRITICAL_ANOMALY"
    
    agent.reset_agent()
    assert agent.status == "NOMINAL"
    assert not agent.threat_alerts
    assert not agent.safety_recommendations
    assert not agent.security_logs
