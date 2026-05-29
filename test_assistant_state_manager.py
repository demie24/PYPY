import pytest
from core.assistant.assistant_state_manager import AssistantStateManager

def test_assistant_state_manager_initial_state():
    manager = AssistantStateManager()
    assert manager.state == "IDLE"
    assert manager.get_state_summary() == {"state": "IDLE"}

def test_assistant_state_manager_valid_transitions():
    manager = AssistantStateManager()
    assert manager.transition_to("LISTENING") is True
    assert manager.state == "LISTENING"
    
    assert manager.transition_to("THINKING") is True
    assert manager.state == "THINKING"
    
    assert manager.transition_to("EXECUTING") is True
    assert manager.state == "EXECUTING"
    
    assert manager.transition_to("RESPONDING") is True
    assert manager.state == "RESPONDING"
    
    assert manager.transition_to("IDLE") is True
    assert manager.state == "IDLE"

def test_assistant_state_manager_invalid_transitions():
    manager = AssistantStateManager()
    # Attempt invalid state
    assert manager.transition_to("INVALID_STATE") is False
    assert manager.state == "ERROR"
