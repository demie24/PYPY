import pytest
from core.assistant.emotion_engine import EmotionEngine

def test_emotion_engine_initial_state():
    engine = EmotionEngine()
    summary = engine.get_emotion_summary()
    assert summary["assistant_mood"] == "calm"
    assert summary["user_mood"] == "calm"

def test_emotion_engine_detect_user_emotion():
    engine = EmotionEngine()
    # Test happy detection
    assert engine.detect_user_emotion("Saya sangat gembira hari ini") == "happy"
    
    # Test sad detection
    assert engine.detect_user_emotion("Sistem ini membuat saya sedih dan kecewa") == "sad"
    
    # Test tired detection
    assert engine.detect_user_emotion("Aduh letih betul la rasa mengantuk") == "tired"
    
    # Test serious/emergency detection
    assert engine.detect_user_emotion("Tolong! Ada kecemasan bahaya sekarang!") == "serious"
    
    # Test calm fallback
    assert engine.detect_user_emotion("Sila jalankan semakan status rutin") == "calm"

def test_emotion_engine_modulate_assistant_emotion_nominal():
    # Empathy matching tests
    assert EmotionEngine().modulate_assistant_emotion("happy", grid_critical=False) == "happy"
    assert EmotionEngine().modulate_assistant_emotion("sad", grid_critical=False) == "sad"
    assert EmotionEngine().modulate_assistant_emotion("tired", grid_critical=False) == "tired"
    assert EmotionEngine().modulate_assistant_emotion("serious", grid_critical=False) == "focused"
    assert EmotionEngine().modulate_assistant_emotion("calm", grid_critical=False) == "calm"

def test_emotion_engine_modulate_assistant_emotion_critical_override():
    engine = EmotionEngine()
    
    # Under grid critical threat, assistant mood MUST immediately override to serious regardless of user mood
    assert engine.modulate_assistant_emotion("happy", grid_critical=True) == "serious"
    assert engine.modulate_assistant_emotion("calm", grid_critical=True) == "serious"
    assert engine.modulate_assistant_emotion("sad", grid_critical=True) == "serious"
    
    summary = engine.get_emotion_summary()
    assert summary["assistant_mood"] == "serious"
