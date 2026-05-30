import pytest
from core.assistant.adaptive_dialogue_engine import AdaptiveDialogueEngine

def test_ambiguity_latency_target():
    engine = AdaptiveDialogueEngine()
    
    # Phrase with missing target bus
    phrase = "check latency"
    intent = {"category": "CHECK_LATENCY", "action": "measure", "parameters": {}}
    
    status = engine.check_ambiguity(phrase, intent)
    assert status["dialogue_state"] == "AWAITING_CLARIFICATION"
    assert status["parameter_needed"] == "target_bus"
    assert "Bus 5 atau Bus 7" in status["clarification_question"]
    
    # Resolve it
    res = engine.resolve_clarification("Bus 5")
    assert res["status"] == "SUCCESS"
    assert res["resolved_intent"]["parameters"]["target"] == "Bus_5"
    assert engine.state == "RESOLVED"

def test_ambiguity_relay_breaker():
    engine = AdaptiveDialogueEngine()
    
    phrase = "monitor relay please"
    intent = {"category": "MONITOR", "action": "relay_status", "parameters": {}}
    
    status = engine.check_ambiguity(phrase, intent)
    assert status["dialogue_state"] == "AWAITING_CLARIFICATION"
    assert status["parameter_needed"] == "relay_line"
    
    res = engine.resolve_clarification("L4_5")
    assert res["status"] == "SUCCESS"
    assert res["resolved_intent"]["parameters"]["target"] == "L4_5"

def test_ambiguity_workflow_name():
    engine = AdaptiveDialogueEngine()
    
    phrase = "trigger workflow"
    intent = {"category": "TRIGGER", "action": "run_workflow", "parameters": {}}
    
    status = engine.check_ambiguity(phrase, intent)
    assert status["dialogue_state"] == "AWAITING_CLARIFICATION"
    assert status["parameter_needed"] == "workflow_name"
    
    res = engine.resolve_clarification("status check")
    assert res["status"] == "SUCCESS"
    assert res["resolved_intent"]["parameters"]["workflow_name"] == "system_status_check"

def test_clear_dialogue():
    engine = AdaptiveDialogueEngine()
    engine.check_ambiguity("check latency", {"category": "LATENCY"})
    assert engine.state == "AWAITING_CLARIFICATION"
    
    engine.clear_dialogue()
    assert engine.state == "IDLE"
    assert engine.pending_intent is None
