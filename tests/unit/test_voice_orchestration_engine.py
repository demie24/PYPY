import pytest
import time
from core.assistant.voice_orchestration_engine import VoiceOrchestrationEngine

def test_initial_voice_orchestration_state():
    engine = VoiceOrchestrationEngine()
    status = engine.get_status_summary()
    assert status["voice_state"] == "IDLE"
    assert status["session_active"] is False
    assert status["session_id"] is None
    assert status["total_sessions"] == 0

def test_voice_session_lifecycle():
    engine = VoiceOrchestrationEngine(session_timeout=1.0)
    
    # Start session
    session_id = engine.start_session()
    assert session_id is not None
    assert engine.is_session_active() is True
    
    status = engine.get_status_summary()
    assert status["voice_state"] == "WAKING"
    assert status["session_active"] is True
    assert status["session_id"] == session_id
    assert status["total_sessions"] == 1
    
    # Tick session (extends expiry)
    engine.tick_session()
    assert engine.is_session_active() is True
    
    # Transition states
    engine.transition_to("LISTENING")
    assert engine.state == "LISTENING"
    
    engine.transition_to("THINKING")
    assert engine.state == "THINKING"
    
    engine.transition_to("SPEAKING")
    assert engine.state == "SPEAKING"
    
    # End session manually
    engine.end_session()
    assert engine.is_session_active() is False
    assert engine.state == "IDLE"

def test_voice_session_timeout():
    engine = VoiceOrchestrationEngine(session_timeout=0.1)
    engine.start_session()
    assert engine.is_session_active() is True
    
    # Wait for session expiry
    time.sleep(0.15)
    assert engine.is_session_active() is False
    assert engine.state == "IDLE"

def test_invalid_state_transitions():
    engine = VoiceOrchestrationEngine()
    engine.transition_to("INVALID_STATE")
    assert engine.state == "IDLE"  # remains IDLE
