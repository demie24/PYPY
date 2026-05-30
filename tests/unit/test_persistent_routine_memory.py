import pytest
import os
from core.assistant.persistent_routine_memory import PersistentRoutineMemory

def test_persistent_memory_io(tmp_path):
    mem_file = os.path.join(tmp_path, "test_routine.json")
    memory = PersistentRoutineMemory(file_path=mem_file)
    
    # Empty summary
    summary = memory.get_status_summary()
    assert summary["total_interactions"] == 0
    
    # Add interaction (Simulate Morning trigger)
    # Hour 9 -> MORNING bin
    import time
    from datetime import datetime
    # Let's specify exact epoch timestamp for Hour 9 (e.g. May 30 2026, 09:00:00)
    ts = datetime(2026, 5, 30, 9, 0, 0).timestamp() * 1000.0
    memory.add_interaction("check system latency", "MEASURE_LATENCY", timestamp_ms=ts)
    
    # Add 3 interactions to meet threshold of 3
    memory.add_interaction("check system latency", "MEASURE_LATENCY", timestamp_ms=ts)
    memory.add_interaction("check system latency", "MEASURE_LATENCY", timestamp_ms=ts)
    
    summary = memory.get_status_summary()
    assert summary["total_interactions"] == 3
    assert summary["recurring_count"] == 1
    assert summary["recurring_actions"][0]["dominant_bin"] == "MORNING"
    assert summary["recurring_actions"][0]["confidence"] == 0.6  # 3/5
    
    # Reload and assert persistence
    new_memory = PersistentRoutineMemory(file_path=mem_file)
    new_summary = new_memory.get_status_summary()
    assert new_summary["total_interactions"] == 3
    assert new_summary["recurring_count"] == 1
    
    # Clear memory
    new_memory.clear_memory()
    assert not os.path.exists(mem_file)
    assert new_memory.get_status_summary()["total_interactions"] == 0
