import pytest
from core.assistant.assistant_reasoning_engine import AssistantReasoningEngine

def test_reasoning_nominal_state():
    engine = AssistantReasoningEngine()
    
    # Nominal grid status, YouTube request
    intent = {
        "category": "COMMAND",
        "action": "open_youtube",
        "confidence": 0.85,
        "parameters": {}
    }
    grid_state = {
        "threat": {"threat_score": 15.0}
    }
    
    result = engine.reason(intent=intent, context={}, emotion={}, grid_state=grid_state)
    assert result["should_execute"] is True
    assert result["resolved_action"] == "open_youtube"
    assert result["webhook_trigger"] is None
    assert result["grid_critical"] is False
    assert any("evaluated: 15.0%" in log for log in result["reasoning_logs"])

def test_reasoning_safety_override():
    engine = AssistantReasoningEngine()
    
    # Critical grid status, YouTube request
    intent = {
        "category": "COMMAND",
        "action": "open_youtube",
        "confidence": 0.90,
        "parameters": {}
    }
    grid_state = {
        "threat": {"threat_score": 75.2}
    }
    
    result = engine.reason(intent=intent, context={}, emotion={}, grid_state=grid_state)
    
    # Safety Override redirects open_youtube to get_system_status
    assert result["should_execute"] is True
    assert result["resolved_action"] == "get_system_status"
    assert result["grid_critical"] is True
    assert result["webhook_trigger"] == "n8n_security_alert"
    assert any("SAFETY OVERRIDE" in log for log in result["reasoning_logs"])

def test_reasoning_automation_planning():
    engine = AssistantReasoningEngine()
    
    # Grid critical, open dashboard action
    intent = {
        "category": "COMMAND",
        "action": "open_dashboard",
        "confidence": 0.95,
        "parameters": {}
    }
    grid_state = {
        "threat": {"threat_score": 82.0}
    }
    
    result = engine.reason(intent=intent, context={}, emotion={}, grid_state=grid_state)
    assert result["should_execute"] is True
    assert result["resolved_action"] == "open_dashboard"
    assert result["webhook_trigger"] == "n8n_security_alert"
    
    # Grid nominal, system status action (leads to n8n_restoration)
    intent2 = {
        "category": "COMMAND",
        "action": "get_system_status",
        "confidence": 0.95,
        "parameters": {}
    }
    grid_state2 = {
        "threat": {"threat_score": 10.0}
    }
    result2 = engine.reason(intent=intent2, context={}, emotion={}, grid_state=grid_state2)
    assert result2["webhook_trigger"] == "n8n_restoration"

def test_reasoning_followup_recommendation():
    engine = AssistantReasoningEngine()
    
    # Critical status check followup recommendation
    intent = {
        "category": "COMMAND",
        "action": "get_system_status",
        "confidence": 0.95,
        "parameters": {}
    }
    grid_state = {
        "threat": {"threat_score": 90.0}
    }
    result = engine.reason(intent=intent, context={}, emotion={}, grid_state=grid_state)
    assert result["followup_recommendation"] == "Engage FLISR auto mode or lock out compromised ports."
    
    # Dashboard check recommendation
    intent2 = {
        "category": "COMMAND",
        "action": "open_dashboard",
        "confidence": 0.95,
        "parameters": {}
    }
    result2 = engine.reason(intent=intent2, context={}, emotion={}, grid_state=grid_state)
    assert result2["followup_recommendation"] == "Review active hardware twin alerts."
