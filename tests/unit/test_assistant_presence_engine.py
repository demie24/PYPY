import pytest
import time
from core.assistant.assistant_presence_engine import AssistantPresenceEngine

def test_initial_presence_state():
    engine = AssistantPresenceEngine()
    summary = engine.get_status_summary("IDLE")
    assert summary["attention_state"] == "ATTENTIVE"
    assert summary["breathing_frequency_hz"] == 1.0
    assert -1.0 <= summary["breathing_coordinate"] <= 1.0

def test_attention_focus_states():
    engine = AssistantPresenceEngine()
    
    # Active session or active attention -> FOCUS
    engine.update_attention(active_session=True, active_attention=False)
    assert engine.attention_state == "FOCUS"
    
    # Active attention window -> FOCUS
    engine.update_attention(active_session=False, active_attention=True)
    assert engine.attention_state == "FOCUS"
    
    # Idle for short time -> ATTENTIVE
    engine.update_attention(active_session=False, active_attention=False)
    assert engine.attention_state == "ATTENTIVE"
    
    # Simulate idle for > 15 seconds -> DIVERTED
    engine.last_interaction_time = time.time() - 16.0
    engine.update_attention(active_session=False, active_attention=False)
    assert engine.attention_state == "DIVERTED"

def test_breathing_frequencies_by_state():
    engine = AssistantPresenceEngine()
    
    # IDLE frequency
    assert engine.get_status_summary("IDLE")["breathing_frequency_hz"] == 1.0
    
    # THINKING frequency
    assert engine.get_status_summary("THINKING")["breathing_frequency_hz"] == 0.5
    
    # RESPONDING frequency
    assert engine.get_status_summary("RESPONDING")["breathing_frequency_hz"] == 1.5
    
    # EXECUTING frequency
    assert engine.get_status_summary("EXECUTING")["breathing_frequency_hz"] == 1.5
    
    # ERROR frequency
    assert engine.get_status_summary("ERROR")["breathing_frequency_hz"] == 2.2

def test_pacing_delay_modulation():
    engine = AssistantPresenceEngine()
    
    # Check pacing delays for nominal grid
    assert engine.calculate_pacing_delay("excited", grid_critical=False) == 0.15
    assert engine.calculate_pacing_delay("serious", grid_critical=False) == 0.30
    assert engine.calculate_pacing_delay("focused", grid_critical=False) == 0.30
    assert engine.calculate_pacing_delay("calm", grid_critical=False) == 0.50
    assert engine.calculate_pacing_delay("tired", grid_critical=False) == 1.10
    
    # Check immediate bypass pacing delay when grid is critical
    assert engine.calculate_pacing_delay("tired", grid_critical=True) == 0.0
    assert engine.calculate_pacing_delay("calm", grid_critical=True) == 0.0
