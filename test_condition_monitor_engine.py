import pytest
import time
from core.assistant.condition_monitor_engine import ConditionMonitorEngine

def test_register_and_remove_watch():
    engine = ConditionMonitorEngine()
    
    # Check default watches are registered
    summary = engine.get_status_summary()
    assert summary["watches_count"] == 3
    assert any(w["condition_id"] == "high_latency_watch" for w in summary["registered_watches"])
    
    # Register custom watch
    engine.register_watch("custom_volt", "telemetry_threshold", "voltage_ms", ">", 1.2, cooldown=10.0)
    summary_new = engine.get_status_summary()
    assert summary_new["watches_count"] == 4
    
    # Remove watch
    success = engine.remove_watch("custom_volt")
    assert success is True
    assert engine.get_status_summary()["watches_count"] == 3
    
    # Remove non-existent
    success_none = engine.remove_watch("fake_watch")
    assert success_none is False

def test_scan_and_cooldown():
    engine = ConditionMonitorEngine()
    
    # Override/register watches with very short cooldowns for testing
    engine.register_watch(
        condition_id="temp_watch",
        watch_type="telemetry_threshold",
        target_field="latency_ms",
        operator=">",
        threshold=100.0,
        cooldown=0.5
    )
    
    # Mock states - below threshold
    grid_state = {"telemetry": {}, "threat": {"threat_score": 20.0}}
    hardware_state = {"latency_ms": 50.0}
    
    triggered = engine.scan(grid_state, hardware_state)
    assert len(triggered) == 0
    
    # Mock states - exceeds threshold
    hardware_state["latency_ms"] = 150.0
    triggered = engine.scan(grid_state, hardware_state)
    assert len(triggered) == 1
    assert triggered[0]["condition_id"] == "temp_watch"
    assert triggered[0]["current_value"] == 150.0
    
    # Scan again immediately, should be blocked by cooldown
    triggered_cooldown = engine.scan(grid_state, hardware_state)
    assert len(triggered_cooldown) == 0
    
    # Wait for cooldown to expire
    time.sleep(0.55)
    triggered_post = engine.scan(grid_state, hardware_state)
    assert len(triggered_post) == 1
    assert triggered_post[0]["condition_id"] == "temp_watch"
