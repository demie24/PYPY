import pytest
import time
from core.assistant.wake_word_manager import WakeWordManager

def test_wake_word_detection_success():
    manager = WakeWordManager(attention_timeout=1.0)
    
    # Matching wake words
    result = manager.detect_wake_word("hey pypy, show me grid status")
    assert result["detected"] is True
    assert result["wake_word"] == "hey pypy"
    assert result["confidence"] == 1.0
    assert result["attention_active"] is True
    
    # Verify status summary
    status = manager.get_status_summary()
    assert status["attention_active"] is True
    assert status["last_wake_word"] == "hey pypy"
    assert status["last_confidence"] == 1.0
    assert status["time_remaining"] > 0.0

def test_wake_word_false_activation_protection():
    manager = WakeWordManager()
    
    # Non-matching words
    result = manager.detect_wake_word("hello there, is the grid offline?")
    assert result["detected"] is False
    assert result["wake_word"] is None
    assert result["confidence"] == 0.0
    assert result["attention_active"] is False

def test_attention_lockout_and_expiration():
    # Set short timeout for testing expiration statefully
    manager = WakeWordManager(attention_timeout=0.2)
    
    # Detect wake word
    result = manager.detect_wake_word("baby, help me")
    assert result["detected"] is True
    assert manager.is_attention_locked() is True
    
    # Wait for attention window to expire
    time.sleep(0.3)
    assert manager.is_attention_locked() is False
    assert manager.get_time_remaining() == 0.0

def test_extend_and_reset_attention():
    manager = WakeWordManager(attention_timeout=1.0)
    manager.detect_wake_word("assistant, status")
    assert manager.is_attention_locked() is True
    
    # Extend attention window
    manager.extend_attention(duration=5.0)
    assert manager.get_time_remaining() > 2.0
    
    # Reset attention state
    manager.reset_attention()
    assert manager.is_attention_locked() is False
    assert manager.get_time_remaining() == 0.0
    assert manager.last_wake_word is None
