import pytest
from typing import Dict, Any
from unittest.mock import MagicMock
from core.assistant.orchestration_planner_bridge import OrchestrationPlannerBridge

def test_confidence_and_safety_nominal():
    bridge = OrchestrationPlannerBridge(confidence_threshold=0.50, min_stability=30.0)
    
    # Nominal case: confidence = 0.80, stability = 45.0%
    grid_state = {
        "threat": {
            "confidence": 0.80,
            "threat_score": 60.0
        },
        "telemetry": {
            "stability_index": 45.0
        }
    }
    
    step = {
        "objective": "TRIGGER_WORKFLOW",
        "parameters": {
            "workflow_name": "emergency_load_shed"
        }
    }
    
    res = bridge.evaluate_confidence_and_safety(step, grid_state)
    assert res["status"] == "SUCCESS"

def test_confidence_too_low():
    bridge = OrchestrationPlannerBridge(confidence_threshold=0.50, min_stability=30.0)
    
    # Rejection: confidence = 0.40, stability = 50%
    grid_state = {
        "threat": {
            "confidence": 0.40,
            "threat_score": 60.0
        },
        "telemetry": {
            "stability_index": 50.0
        }
    }
    
    step = {
        "objective": "SHED_LOAD",
        "parameters": {}
    }
    
    res = bridge.evaluate_confidence_and_safety(step, grid_state)
    assert res["status"] == "FAILED"
    assert "Confidence score too low" in res["error"]

def test_stability_too_low_escalation():
    bridge = OrchestrationPlannerBridge(confidence_threshold=0.50, min_stability=30.0)
    
    # Escalation: confidence = 0.70, stability = 25%
    grid_state = {
        "threat": {
            "confidence": 0.70,
            "threat_score": 80.0
        },
        "telemetry": {
            "stability_index": 25.0
        }
    }
    
    step = {
        "objective": "TRIP_BREAKER",
        "parameters": {}
    }
    
    res = bridge.evaluate_confidence_and_safety(step, grid_state)
    assert res["status"] == "FAILED"
    assert res["error"] == "escalate_to_operator"
    assert "Grid stability collapsed below 30%" in res["reason"]

def test_execute_step_checks():
    bridge = OrchestrationPlannerBridge(confidence_threshold=0.50, min_stability=30.0)
    
    # Mock systems
    n8n_mock = MagicMock()
    wf_mock = MagicMock()
    rem_mock = MagicMock()
    mqtt_mock = MagicMock()
    
    grid_state = {
        "threat": {"confidence": 0.80, "threat_score": 60.0},
        "telemetry": {"latency_ms": 120.0, "stability_index": 55.0}
    }
    
    # 1. MEASURE_LATENCY
    step_lat = {"objective": "MEASURE_LATENCY", "parameters": {}}
    res_lat = bridge.execute_step("chain_1", step_lat, grid_state, n8n_mock, wf_mock, rem_mock, mqtt_mock)
    assert res_lat["status"] == "SUCCESS"
    assert res_lat["result"] == 120.0
    
    # 2. CHECK_LIMIT
    step_lim = {"objective": "CHECK_LIMIT", "parameters": {"field": "latency_ms", "operator": ">", "threshold": 100.0}}
    res_lim = bridge.execute_step("chain_1", step_lim, grid_state, n8n_mock, wf_mock, rem_mock, mqtt_mock)
    assert res_lim["status"] == "SUCCESS"
    assert res_lim["result"] == "threshold_exceeded"
    
    # 3. SCHEDULE_REMINDER
    rem_mock.add_reminder.return_value = {"status": "SCHEDULED"}
    step_rem = {"objective": "SCHEDULE_REMINDER", "parameters": {"text": "Alert", "delay_sec": 5.0}}
    res_rem = bridge.execute_step("chain_1", step_rem, grid_state, n8n_mock, wf_mock, rem_mock, mqtt_mock)
    assert res_rem["status"] == "SCHEDULED"
    rem_mock.add_reminder.assert_called_with("Alert", 5.0)
    
    # 4. MONITOR_RELAY success
    grid_state_stable = {
        "relay_unstable": False
    }
    step_mon = {"objective": "MONITOR_RELAY", "parameters": {"target": "relay_unstable", "expected_value": False}}
    res_mon = bridge.execute_step("chain_1", step_mon, grid_state_stable, n8n_mock, wf_mock, rem_mock, mqtt_mock)
    assert res_mon["status"] == "SUCCESS"
    assert res_mon["result"] == "stability_reached"
    
    # 5. MONITOR_RELAY paused
    grid_state_unstable = {
        "relay_unstable": True
    }
    res_mon_p = bridge.execute_step("chain_1", step_mon, grid_state_unstable, n8n_mock, wf_mock, rem_mock, mqtt_mock)
    assert res_mon_p["status"] == "PAUSED"
