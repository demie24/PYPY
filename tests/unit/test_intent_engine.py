import pytest
from core.assistant.intent_engine import IntentEngine

def test_intent_engine_empty_input():
    engine = IntentEngine()
    result = engine.detect_intent("")
    assert result["category"] == "UNKNOWN"
    assert result["action"] is None
    assert result["confidence"] == 0.0

def test_intent_engine_direct_command():
    engine = IntentEngine()
    # Test open_youtube keyword trigger
    result1 = engine.detect_intent("Tolong main youtube")
    assert result1["category"] == "COMMAND"
    assert result1["action"] == "open_youtube"
    assert result1["confidence"] == 0.95

    # Test open_browser keyword trigger
    result2 = engine.detect_intent("buka browser chrome")
    assert result2["category"] == "COMMAND"
    assert result2["action"] == "open_browser"
    
    # Test open_dashboard keyword trigger
    result3 = engine.detect_intent("tunjukkan scada dashboard")
    assert result3["category"] == "COMMAND"
    assert result3["action"] == "open_dashboard"

def test_intent_engine_utilities():
    engine = IntentEngine()
    result = engine.detect_intent("pukul berapa sekarang?")
    assert result["category"] == "UTILITY"
    assert result["action"] == "get_time"

def test_intent_engine_greetings_and_fallback():
    engine = IntentEngine()
    # Test greetings fallback
    result1 = engine.detect_intent("hello assistant")
    assert result1["category"] == "CONVERSATION"
    assert result1["action"] == "greeting"
    assert result1["confidence"] == 0.80

    # Test generic chat fallback
    result2 = engine.detect_intent("bagaimana cuaca hari ini?")
    assert result2["category"] == "CONVERSATION"
    assert result2["action"] == "generic_chat"
    assert result2["confidence"] == 0.50

def test_intent_engine_parameters():
    engine = IntentEngine()
    result = engine.detect_intent("status zone 5")
    assert "zone" in result["parameters"]
    assert result["parameters"]["zone"] == "zone_5"
