import pytest
from core.assistant.semantic_intent_engine import SemanticIntentEngine

def test_semantic_intent_engine_empty_input():
    engine = SemanticIntentEngine()
    result = engine.detect_intent("")
    assert result["category"] == "UNKNOWN"
    assert result["action"] is None
    assert result["confidence"] == 0.0

def test_semantic_intent_engine_jaccard_fuzzy():
    # Jaccard set overlap checks
    # Threshold is 0.40. "youtube" set: {"youtube", "yt", "main", "pasang"}
    engine = SemanticIntentEngine(jaccard_threshold=0.40)
    
    # Input has "youtube", intersection: {"youtube"}, union of input and ref.
    # Input: "buka youtube" -> {"buka", "youtube"}. Ref: {"youtube", "yt", "main", "pasang"}
    # intersection: {"youtube"} (1). union: {"buka", "youtube", "yt", "main", "pasang"} (5).
    # Jaccard = 1/5 = 0.20. BUT word "youtube" matches ref_set, which boosts it to 0.45.
    # Let's check:
    result = engine.detect_intent("buka youtube")
    assert result["category"] == "COMMAND"
    assert result["action"] == "open_youtube"
    assert result.get("is_fuzzy") is True
    assert result["confidence"] >= 0.40

def test_semantic_intent_engine_followup_continuity():
    engine = SemanticIntentEngine()
    
    # Resolving follow-up references
    result = engine.detect_intent("buka balik yang tadi tu", previous_action="open_dashboard")
    assert result["category"] == "COMMAND"
    assert result["action"] == "open_dashboard"
    assert result["is_followup"] is True
    assert result["confidence"] == 0.90
    
    result2 = engine.detect_intent("macam mana yang tadi", previous_action="get_time")
    assert result2["category"] == "UTILITY"
    assert result2["action"] == "get_time"
    assert result2["is_followup"] is True

def test_semantic_intent_engine_parameter_parsing():
    engine = SemanticIntentEngine()
    
    # Check bus parameter matching
    result = engine.detect_intent("status bus 3")
    assert "bus" in result["parameters"]
    assert result["parameters"]["bus"] == "Bus_3"
    
    # Check zone parameter matching
    result2 = engine.detect_intent("status zone 7")
    assert "zone" in result2["parameters"]
    assert result2["parameters"]["zone"] == "zone_7"

def test_semantic_intent_engine_greetings_and_generic():
    engine = SemanticIntentEngine()
    
    result = engine.detect_intent("hi assistant")
    assert result["category"] == "CONVERSATION"
    assert result["action"] == "greeting"
    
    result2 = engine.detect_intent("saya lapar gila")
    assert result2["category"] == "CONVERSATION"
    assert result2["action"] == "generic_chat"
