import pytest
import time
from core.assistant.contextual_memory_engine import ContextualMemoryEngine

def test_contextual_memory_basic_tracking():
    engine = ContextualMemoryEngine()
    
    # Empty summary checks
    summary = engine.get_memory_summary()
    assert summary["active_thread_id"] is None
    assert len(summary["active_messages"]) == 0
    assert summary["thread_count"] == 0
    
    # Add interaction sets active thread
    engine.add_interaction("user", "Hello grid assistant")
    summary = engine.get_memory_summary()
    assert summary["active_thread_id"] is not None
    assert len(summary["active_messages"]) == 1
    assert summary["thread_count"] == 1
    
    # Adding more interactions stays on the same thread
    first_thread_id = summary["active_thread_id"]
    engine.add_interaction("assistant", "Hi operator!")
    summary2 = engine.get_memory_summary()
    assert summary2["active_thread_id"] == first_thread_id
    assert len(summary2["active_messages"]) == 2

def test_contextual_memory_timeout():
    # Use small timeout to test expiry
    engine = ContextualMemoryEngine(thread_timeout=0.1)
    
    engine.add_interaction("user", "first message")
    first_thread = engine.active_thread_id
    
    # Wait for timeout to expire
    time.sleep(0.15)
    
    engine.add_interaction("user", "second message")
    second_thread = engine.active_thread_id
    
    assert first_thread != second_thread
    assert engine.get_memory_summary()["thread_count"] == 2

def test_contextual_memory_consolidation():
    # Set limit to 5 to trigger consolidation early
    engine = ContextualMemoryEngine(limit=5)
    
    # Add 6 messages. 
    # With a limit of 5, the 6th message should trigger consolidation.
    # The consolidation collapses the first 4 messages into a single system summary.
    # The remaining messages in the thread are the system summary (1) + messages 5 & 6 (2) = 3 total messages.
    engine.add_interaction("user", "msg1")
    engine.add_interaction("assistant", "resp1")
    engine.add_interaction("user", "msg2")
    engine.add_interaction("assistant", "resp2")
    engine.add_interaction("user", "msg3")
    engine.add_interaction("assistant", "resp3")
    
    messages = engine.threads[engine.active_thread_id]["messages"]
    assert len(messages) == 3
    assert messages[0]["role"] == "system_summary"
    assert "msg1" in messages[0]["text"]
    assert "resp2" in messages[0]["text"]

def test_contextual_memory_reference_caching():
    engine = ContextualMemoryEngine()
    
    # Check reference caching on interaction
    engine.add_interaction(
        role="user", 
        text="status zone 4", 
        intent_action="get_system_status",
        entities={"zone": "zone_4"}
    )
    
    # Should recall reference
    assert engine.recall_reference("zone") == "zone_4"
    assert engine.recall_reference("bus") is None
    
    summary = engine.get_memory_summary()
    assert summary["recent_references"]["zone"] == "zone_4"

def test_contextual_memory_clear():
    engine = ContextualMemoryEngine()
    engine.add_interaction("user", "hello")
    engine.clear_memory()
    
    summary = engine.get_memory_summary()
    assert summary["active_thread_id"] is None
    assert len(summary["recent_references"]) == 0
    assert summary["thread_count"] == 0
