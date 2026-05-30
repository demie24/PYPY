import pytest
from core.assistant.pattern_awareness_engine import PatternAwarenessEngine

def test_voltage_oscillation_detection():
    engine = PatternAwarenessEngine()
    
    # Simulate swings
    engine.analyze_patterns({"telemetry": {"Bus_5_voltage": 1.05}}, {})
    engine.analyze_patterns({"telemetry": {"Bus_5_voltage": 0.98}}, {})
    patterns = engine.analyze_patterns({"telemetry": {"Bus_5_voltage": 1.06}}, {})
    
    assert len(patterns) == 1
    assert patterns[0]["pattern_id"] == "voltage_oscillation_bus_5"
    assert patterns[0]["confidence_score"] == 0.5
    
    # Increase swings
    engine.analyze_patterns({"telemetry": {"Bus_5_voltage": 0.96}}, {})
    patterns = engine.analyze_patterns({"telemetry": {"Bus_5_voltage": 1.08}}, {})
    assert patterns[0]["occurrence_count"] == 5
    assert patterns[0]["confidence_score"] == 0.7
    
    # Reset
    engine.reset_counters()
    assert len(engine.analyze_patterns({"telemetry": {"Bus_5_voltage": 1.0}}, {})) == 0

def test_workflow_failure_loop_detection():
    engine = PatternAwarenessEngine()
    
    # Simulate workflow failures
    workflows_summary = {
        "completed_workflows": [
            {"workflow_name": "system_status_check", "status": "FAILED"},
            {"workflow_name": "system_status_check", "status": "FAILED"}
        ]
    }
    
    patterns = engine.analyze_patterns({}, workflows_summary)
    assert len(patterns) == 1
    assert patterns[0]["pattern_id"] == "failure_loop_system_status_check"
    assert patterns[0]["confidence_score"] == 0.8  # 0.4 + 2 * 0.2
