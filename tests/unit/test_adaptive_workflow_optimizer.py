import pytest
from core.assistant.adaptive_workflow_optimizer import AdaptiveWorkflowOptimizer

def test_optimization_recommendations():
    optimizer = AdaptiveWorkflowOptimizer()
    
    # Nominal case evaluation -> recommend TRIM_DELAY
    grid_state = {"threat": {"threat_score": 15.0}, "telemetry": {"latency_ms": 30.0}}
    predicted_timings = {"system_status_check": 4.5}
    
    recs = optimizer.evaluate_efficiency(grid_state, {}, predicted_timings)
    assert len(recs) == 1
    assert recs[0]["workflow_name"] == "system_status_check"
    assert recs[0]["optimization_type"] == "TRIM_DELAY"
    assert recs[0]["status"] == "PENDING_APPROVAL"
    
    # High threat case evaluation -> recommend INFLATE_LOCKOUT
    critical_grid = {"threat": {"threat_score": 85.0}, "telemetry": {"latency_ms": 40.0}}
    recs = optimizer.evaluate_efficiency(critical_grid, {}, {})
    assert len(recs) == 1
    assert recs[0]["workflow_name"] == "emergency_load_shed"
    assert recs[0]["optimization_type"] == "INFLATE_LOCKOUT"

def test_operator_approval_locks():
    optimizer = AdaptiveWorkflowOptimizer()
    grid_state = {"threat": {"threat_score": 15.0}, "telemetry": {"latency_ms": 30.0}}
    optimizer.evaluate_efficiency(grid_state, {}, {"system_status_check": 4.0})
    
    # Delay remains default before approval
    assert optimizer.get_optimized_delay("system_status_check", 5.0) == 5.0
    
    # Approve recommendation
    res = optimizer.approve_recommendation("system_status_check")
    assert res["status"] == "SUCCESS"
    
    # Delay is now optimized
    assert optimizer.get_optimized_delay("system_status_check", 5.0) == 3.5
