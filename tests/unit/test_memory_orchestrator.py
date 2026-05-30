import pytest
from core.assistant.memory_orchestrator import MemoryOrchestrator

def test_memory_orchestrator_initial_state():
    memory = MemoryOrchestrator()
    summary = memory.get_memory_summary()
    assert len(summary["interactions"]) == 0
    assert summary["user_preferences"]["name"] == "Operator"
    assert len(summary["command_history"]) == 0

def test_memory_orchestrator_add_interaction():
    memory = MemoryOrchestrator()
    memory.add_interaction("user", "Hello assistant")
    memory.add_interaction("assistant", "Hello Operator, can I help you?")
    
    summary = memory.get_memory_summary()
    assert len(summary["interactions"]) == 2
    assert summary["interactions"][0]["role"] == "user"
    assert summary["interactions"][0]["text"] == "Hello assistant"
    assert summary["interactions"][1]["role"] == "assistant"
    assert summary["interactions"][1]["text"] == "Hello Operator, can I help you?"

def test_memory_orchestrator_command_history():
    memory = MemoryOrchestrator()
    memory.record_command("open_youtube")
    memory.record_command("get_time")
    
    summary = memory.get_memory_summary()
    assert len(summary["command_history"]) == 2
    assert summary["command_history"] == ["open_youtube", "get_time"]

def test_memory_orchestrator_summarization():
    # Set limit low to trigger summarization
    memory = MemoryOrchestrator(limit=4)
    memory.add_interaction("user", "1")
    memory.add_interaction("assistant", "2")
    memory.add_interaction("user", "3")
    memory.add_interaction("assistant", "4")
    
    # 5th interaction will trigger summarize_memory() which summarizes the first 4 and leaves the 5th
    memory.add_interaction("user", "5")
    
    summary = memory.get_memory_summary()
    interactions = summary["interactions"]
    
    # Should have consolidated the first 4 into a summary, plus the 5th interaction
    assert len(interactions) == 2
    assert interactions[0]["role"] == "system_summary"
    assert "user: 1" in interactions[0]["text"]
    assert "assistant: 2" in interactions[0]["text"]
    assert interactions[1]["role"] == "user"
    assert interactions[1]["text"] == "5"

def test_memory_orchestrator_preferences_and_clear():
    memory = MemoryOrchestrator()
    memory.set_user_preference("name", "Syed")
    memory.add_interaction("user", "testing")
    memory.record_command("open_browser")
    
    memory.clear_memory()
    
    summary = memory.get_memory_summary()
    assert len(summary["interactions"]) == 0
    assert len(summary["command_history"]) == 0
    # Preferences should be retained even when clearing rolling message buffers
    assert summary["user_preferences"]["name"] == "Syed"
