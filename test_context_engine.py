import pytest
import time
from core.assistant.context_engine import ContextEngine

def test_context_engine_initial_state():
    engine = ContextEngine()
    summary = engine.get_context_summary()
    assert summary["session_active"] is False
    assert summary["current_topic"] is None
    assert summary["interaction_depth"] == 0
    assert summary["previous_action"] is None

def test_context_engine_update_context():
    engine = ContextEngine()
    intent = {"category": "COMMAND", "action": "open_youtube", "confidence": 0.95, "parameters": {}}
    
    engine.update_context(intent, "LISTENING")
    summary = engine.get_context_summary()
    
    assert summary["session_active"] is True
    assert summary["current_topic"] == "open_youtube"
    assert summary["interaction_depth"] == 1
    assert summary["assistant_state"] == "LISTENING"
    assert summary["previous_action"] == "open_youtube"

def test_context_engine_depth_increments():
    engine = ContextEngine()
    intent1 = {"category": "COMMAND", "action": "open_youtube"}
    intent2 = {"category": "UTILITY", "action": "get_time"}
    
    engine.update_context(intent1, "THINKING")
    engine.update_context(intent2, "RESPONDING")
    
    summary = engine.get_context_summary()
    assert summary["interaction_depth"] == 2
    assert summary["current_topic"] == "get_time"
    assert summary["previous_action"] == "get_time"

def test_context_engine_reset():
    engine = ContextEngine()
    intent = {"category": "COMMAND", "action": "open_youtube"}
    
    engine.update_context(intent, "EXECUTING")
    engine.reset_context()
    
    summary = engine.get_context_summary()
    assert summary["session_active"] is False
    assert summary["current_topic"] is None
    assert summary["interaction_depth"] == 0
