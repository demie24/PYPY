import pytest
from core.assistant.decision_engine import DecisionEngine

def test_decision_engine_conversational_route():
    engine = DecisionEngine()
    intent = {"category": "CONVERSATION", "action": "greeting", "confidence": 0.8, "parameters": {}}
    context = {"session_active": True, "interaction_depth": 1}
    emotion = {"assistant_mood": "calm", "user_mood": "calm"}
    
    decision = engine.determine_routing(intent, context, emotion)
    
    assert decision["should_execute"] is False
    assert decision["should_respond"] is True
    assert decision["route"] == "CONVERSATION"
    assert decision["resolved_action"] == "greeting"

def test_decision_engine_command_route():
    engine = DecisionEngine()
    intent = {"category": "COMMAND", "action": "open_browser", "confidence": 0.95, "parameters": {}}
    context = {"session_active": True, "interaction_depth": 2}
    emotion = {"assistant_mood": "calm", "user_mood": "calm"}
    
    decision = engine.determine_routing(intent, context, emotion)
    
    assert decision["should_execute"] is True
    assert decision["should_respond"] is True
    assert decision["route"] == "COMMAND"
    assert decision["resolved_action"] == "open_browser"

def test_decision_engine_low_confidence_blocks_execution():
    engine = DecisionEngine()
    intent = {"category": "COMMAND", "action": "open_browser", "confidence": 0.50, "parameters": {}}
    context = {"session_active": True, "interaction_depth": 2}
    emotion = {"assistant_mood": "calm", "user_mood": "calm"}
    
    decision = engine.determine_routing(intent, context, emotion)
    
    assert decision["should_execute"] is False

def test_decision_engine_safety_override():
    engine = DecisionEngine()
    intent = {"category": "COMMAND", "action": "open_youtube", "confidence": 0.95, "parameters": {}}
    context = {"session_active": True, "interaction_depth": 3}
    # When grid is under critical stress, mood is "serious" or "focused"
    emotion = {"assistant_mood": "serious", "user_mood": "happy"}
    
    decision = engine.determine_routing(intent, context, emotion)
    
    # "open_youtube" should be blocked, and action redirected to "get_system_status"
    assert decision["should_execute"] is True
    assert decision["route"] == "COMMAND"
    assert decision["resolved_action"] == "get_system_status"
