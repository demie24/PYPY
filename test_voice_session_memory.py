import pytest
from core.assistant.voice_session_memory import VoiceSessionMemory

def test_session_initialization():
    memory = VoiceSessionMemory()
    summary = memory.get_session_summary(None)
    assert summary["active_session_id"] is None
    assert summary["session_messages"] == []
    assert summary["total_cached_sessions"] == 0

def test_add_session_interactions():
    memory = VoiceSessionMemory()
    session_id = "test-session-123"
    
    # Add user message
    memory.add_interaction(session_id, "user", "buka dashboard hmi")
    assert memory.latest_voice_text == "buka dashboard hmi"
    
    # Add executed action
    memory.add_interaction(session_id, "user_command", "[Executed: open_dashboard]", action="open_dashboard")
    assert memory.latest_command == "open_dashboard"
    assert memory.recall_last_command(session_id) == "open_dashboard"
    
    # Add assistant response
    memory.add_interaction(session_id, "assistant", "Baik, saya dah bukakan dashboard HMI.")
    
    # Verify session summary
    summary = memory.get_session_summary(session_id)
    assert summary["active_session_id"] == session_id
    assert len(summary["session_messages"]) == 3
    assert summary["session_commands"] == ["open_dashboard"]
    assert summary["latest_command"] == "open_dashboard"
    assert summary["latest_voice_text"] == "buka dashboard hmi"
    assert summary["total_cached_sessions"] == 1

def test_clear_session_and_wipe_all():
    memory = VoiceSessionMemory()
    session_id_1 = "session-1"
    session_id_2 = "session-2"
    
    memory.add_interaction(session_id_1, "user", "hello")
    memory.add_interaction(session_id_2, "user", "world")
    
    assert len(memory.session_memories) == 2
    
    # Clear session 1
    memory.clear_session(session_id_1)
    assert session_id_1 not in memory.session_memories
    assert len(memory.session_memories) == 1
    
    # Wipe all
    memory.clear_all()
    assert len(memory.session_memories) == 0
    assert memory.latest_command is None
    assert memory.latest_voice_text is None
