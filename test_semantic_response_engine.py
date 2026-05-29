import pytest
from core.assistant.semantic_response_engine import SemanticResponseEngine

def test_semantic_response_engine_tts_cleaning():
    engine = SemanticResponseEngine()
    
    # Check cleaning markdown bold, headers, underscores
    text = "### **Status Grid**\nSemua *nominal* dan _ok_ je tadi."
    cleaned = engine.clean_tts(text)
    
    # Headers, bold stars, underscores removed
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "_" not in cleaned
    assert cleaned == "Status Grid\nSemua nominal dan ok je tadi."

def test_semantic_response_greetings():
    engine = SemanticResponseEngine()
    
    reasoning = {"resolved_action": "greeting"}
    action_result = {}
    
    # Excited greeting
    resp_excited = engine.generate_response(reasoning, action_result, {"assistant_mood": "excited"})
    assert "Wah hello" in resp_excited
    assert "operator" in resp_excited
    
    # Serious greeting
    resp_serious = engine.generate_response(reasoning, action_result, {"assistant_mood": "serious"})
    assert "Sistem bersedia" in resp_serious
    
    # Tired greeting
    resp_tired = engine.generate_response(reasoning, action_result, {"assistant_mood": "tired"})
    assert "penat sikit" in resp_tired or "Penat sikit" in resp_tired

def test_semantic_response_actions():
    engine = SemanticResponseEngine()
    
    # Open youtube nominal
    reasoning = {
        "resolved_action": "open_youtube",
        "parameters": {"resolved_from_context": False},
        "grid_critical": False
    }
    action_result = {"payload": {"url": "https://youtube.com"}}
    resp = engine.generate_response(reasoning, action_result, {"assistant_mood": "calm"})
    assert "YouTube" in resp
    assert "je" in resp  # Suffix for calm
    
    # Follow-up YouTube
    reasoning_follow = {
        "resolved_action": "open_youtube",
        "parameters": {"resolved_from_context": True},
        "grid_critical": False
    }
    resp_follow = engine.generate_response(reasoning_follow, action_result, {"assistant_mood": "calm"})
    assert "tadi tu" in resp_follow

def test_semantic_response_grid_critical():
    engine = SemanticResponseEngine()
    
    reasoning = {
        "resolved_action": "get_system_status",
        "parameters": {},
        "grid_critical": True
    }
    action_result = {
        "payload": {
            "stability": "CRITICAL",
            "threat_score": 85.0
        }
    }
    
    # Response must be warning/critical structure in Malay without casual endings
    resp = engine.generate_response(reasoning, action_result, {"assistant_mood": "serious"})
    assert "kritikal" in resp
    assert "threat score 85.0" in resp or "85.0 peratus" in resp
    assert "je" not in resp  # Serious/critical lockout drops casual suffixes
