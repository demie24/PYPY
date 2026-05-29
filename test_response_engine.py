import pytest
from core.assistant.response_engine import ResponseEngine

def test_response_engine_identity():
    engine = ResponseEngine()
    
    # Test identity under happy mood
    res_happy = engine.generate_response("assistant_identity_response", {}, {"assistant_mood": "happy"})
    assert "Hai!" in res_happy
    assert "Seronok dapat bantu" in res_happy
    assert "*" not in res_happy # Voice-friendly formatting constraint
    
    # Test identity under serious mood
    res_serious = engine.generate_response("assistant_identity_response", {}, {"assistant_mood": "serious"})
    assert "keselamatan grid" in res_serious
    assert "ketat" in res_serious

def test_response_engine_system_status():
    engine = ResponseEngine()
    
    # Nominal
    action_result_nominal = {"status": "SUCCESS", "payload": {"stability": "NORMAL", "threat_score": 5.0}}
    res_nominal = engine.generate_response("get_system_status", action_result_nominal, {"assistant_mood": "calm"})
    assert "nominal" in res_nominal or "stabil" in res_nominal
    
    # Critical under serious mood
    action_result_crit = {"status": "SUCCESS", "payload": {"stability": "CRITICAL", "threat_score": 88.5}}
    res_crit = engine.generate_response("get_system_status", action_result_crit, {"assistant_mood": "serious"})
    assert "Bahaya" in res_crit or "kritikal" in res_crit
    assert "88.5" in res_crit

def test_response_engine_open_youtube_serious():
    engine = ResponseEngine()
    action_result = {"status": "SUCCESS", "payload": {"url": "https://www.youtube.com"}}
    
    # Should decline or suggest focusing on grid if serious mood is active
    res = engine.generate_response("open_youtube", action_result, {"assistant_mood": "serious"})
    assert "Maaf" in res or "kecemasan" in res or "fokus" in res

def test_response_engine_greetings():
    engine = ResponseEngine()
    res_greeting = engine.generate_response("greeting", {}, {"assistant_mood": "calm"})
    assert "tugasan" in res_greeting or "salam" in res_greeting or "bantu" in res_greeting
