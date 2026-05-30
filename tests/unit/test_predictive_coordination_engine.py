import pytest
import time
from core.assistant.predictive_coordination_engine import PredictiveCoordinationEngine

def test_predictive_engine_initial_state():
    engine = PredictiveCoordinationEngine()
    summary = engine.get_status_summary()
    assert summary["forecasts_count"] == 0
    assert summary["suggestions_count"] == 0
    assert not summary["latency_history"]

def test_add_latency_and_timing_prediction():
    engine = PredictiveCoordinationEngine()
    engine.add_latency_point(40.0)
    engine.add_latency_point(50.0)
    summary = engine.get_status_summary()
    assert len(summary["latency_history"]) == 2
    
    # Workflow timings
    engine.record_workflow_duration("test_wf", 4.0)
    engine.record_workflow_duration("test_wf", 6.0)
    assert engine.predict_workflow_duration("test_wf") == 5.0

def test_trend_forecasting_and_cooldown():
    engine = PredictiveCoordinationEngine()
    # Populate increasing latency
    engine.add_latency_point(50.0)
    engine.add_latency_point(65.0)
    engine.add_latency_point(85.0)
    
    forecasts = engine.analyze_trends({}, {})
    assert len(forecasts) == 1
    assert forecasts[0]["category"] == "LATENCY_SPIKE"
    
    summary = engine.get_status_summary()
    assert summary["suggestions_count"] == 1
    assert summary["suggestions"][0]["action_type"] == "TRIGGER_WORKFLOW"
    
    # Check cooldown prevents duplicates
    engine.suggestions = []
    engine.analyze_trends({}, {})
    # Cooldown should prevent suggestions from re-populating immediately
    assert len(engine.suggestions) == 0
