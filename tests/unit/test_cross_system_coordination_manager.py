import pytest
from core.assistant.cross_system_coordination_manager import CrossSystemCoordinationManager

def test_sync_state_and_clock_drift():
    manager = CrossSystemCoordinationManager()
    
    # Normal latency -> SYNCED, 0 drift
    grid_state = {"telemetry": {"latency_ms": 45.0}}
    res = manager.tick_synchronization(grid_state, {}, [])
    assert res["sync_state"] == "SYNCED"
    assert res["drift_sec"] == 0.0
    
    # High latency -> DRIFTING, positive drift
    grid_state_drift = {"telemetry": {"latency_ms": 180.0}}
    res = manager.tick_synchronization(grid_state_drift, {}, [])
    assert res["sync_state"] == "DRIFTING"
    assert res["drift_sec"] == 0.08  # (180 - 100) / 1000

def test_optimization_conflict_prevention():
    manager = CrossSystemCoordinationManager()
    
    # Mock TRIM_DELAY recommendation
    recommendations = [{
        "workflow_name": "system_status_check",
        "optimization_type": "TRIM_DELAY",
        "description": "Trim delay",
        "status": "PENDING_APPROVAL"
    }]
    
    # Normal threat -> no conflict
    grid_state_low = {"threat": {"threat_score": 15.0}, "telemetry": {"latency_ms": 40.0}}
    res = manager.tick_synchronization(grid_state_low, {}, recommendations)
    assert res["sync_state"] == "SYNCED"
    assert recommendations[0]["status"] == "PENDING_APPROVAL"
    
    # Critical threat -> conflict override triggered
    grid_state_high = {"threat": {"threat_score": 85.0}, "telemetry": {"latency_ms": 40.0}}
    res = manager.tick_synchronization(grid_state_high, {}, recommendations)
    assert res["sync_state"] == "CONFLICT_RESOLVING"
    assert recommendations[0]["status"] == "BLOCKED"
    assert "Safety overrides optimization" in res["conflict_logs"][0]
