import pytest
import time
from core.assistant.synchronization_awareness_manager import SynchronizationAwarenessManager

def test_sync_manager_initialization():
    manager = SynchronizationAwarenessManager()
    assert "esp32_zone1" in manager.node_drifts
    assert manager.node_drifts["esp32_zone1"]["status"] == "IN_SYNC"
    assert manager.drift_threshold_sec == 0.025
    assert manager.critical_threshold_ticks == 5

def test_update_drift_validation():
    manager = SynchronizationAwarenessManager()
    
    # 1. Update drift within normal bound (< 25ms)
    manager.update_node_drift("esp32_zone1", drift_sec=0.010) # 10ms
    assert manager.node_drifts["esp32_zone1"]["status"] == "IN_SYNC"
    assert manager.node_drifts["esp32_zone1"]["consecutive_skew_ticks"] == 0

    # 2. Exceed threshold (> 25ms) -> status SKEWED
    manager.update_node_drift("esp32_zone1", drift_sec=0.030) # 30ms
    assert manager.node_drifts["esp32_zone1"]["status"] == "SKEWED"
    assert manager.node_drifts["esp32_zone1"]["consecutive_skew_ticks"] == 1

    # 3. Escalate to CRITICAL_SKEW after 5 ticks (since critical limit is 5 ticks)
    for _ in range(5):
        manager.update_node_drift("esp32_zone1", drift_sec=0.030)
    assert manager.node_drifts["esp32_zone1"]["status"] == "CRITICAL_SKEW"
    assert manager.node_drifts["esp32_zone1"]["consecutive_skew_ticks"] > 5

    # 4. Hysteresis recovery logic (must be < 15ms to recover)
    # If we set to 20ms, it is under 25ms threshold, but still above 15ms hysteresis recovery limit
    manager.update_node_drift("esp32_zone1", drift_sec=0.020)
    # remains CRITICAL_SKEW because it didn't clear the 15ms threshold
    assert manager.node_drifts["esp32_zone1"]["status"] == "CRITICAL_SKEW"

    # Set drift to 10ms (< 15ms)
    manager.update_node_drift("esp32_zone1", drift_sec=0.010)
    assert manager.node_drifts["esp32_zone1"]["status"] == "IN_SYNC"
    assert manager.node_drifts["esp32_zone1"]["consecutive_skew_ticks"] == 0

def test_get_skewed_nodes():
    manager = SynchronizationAwarenessManager()
    manager.update_node_drift("esp32_zone1", drift_sec=0.030)
    manager.update_node_drift("esp32_zone2", drift_sec=0.010)
    
    # esp32_zone1 is SKEWED, esp32_zone2 is IN_SYNC
    assert "esp32_zone1" in manager.get_skewed_nodes()
    assert "esp32_zone2" not in manager.get_skewed_nodes()

def test_get_status_summary_and_reset():
    manager = SynchronizationAwarenessManager()
    manager.update_node_drift("esp32_zone1", drift_sec=0.030)
    
    summary = manager.get_status_summary()
    assert summary["max_drift_node"] == "esp32_zone1"
    assert abs(summary["max_drift_ms"] - 30.0) < 0.001
    assert len(summary["warnings"]) == 1
    assert "CLOCK_SKEW_WARNING" in summary["warnings"][0]

    # Elevate to critical
    for _ in range(6):
         manager.update_node_drift("esp32_zone1", drift_sec=0.035)
    summary = manager.get_status_summary()
    assert "CLOCK_SKEW_CRITICAL" in summary["warnings"][0]

    manager.reset_engine()
    assert manager.node_drifts["esp32_zone1"]["status"] == "IN_SYNC"
    assert manager.node_drifts["esp32_zone1"]["drift_sec"] == 0.0
