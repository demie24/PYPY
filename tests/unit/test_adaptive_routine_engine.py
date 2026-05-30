import pytest
from core.assistant.adaptive_routine_engine import AdaptiveRoutineEngine

def test_record_interaction_and_frequencies():
    engine = AdaptiveRoutineEngine(repeat_threshold=3)
    
    # Record unique command interactions
    engine.record_interaction("get_system_status", "check system status please")
    engine.record_interaction("open_dashboard", "buka dashboard hmi")
    
    summary = engine.get_status_summary()
    assert summary["command_frequencies"]["get_system_status"] == 1
    assert summary["command_frequencies"]["open_dashboard"] == 1
    assert summary["routines_count"] == 0

def test_routine_recommendation_trigger():
    # Set repeat threshold = 2
    engine = AdaptiveRoutineEngine(repeat_threshold=2)
    
    # Trigger get_system_status routine
    engine.record_interaction("get_system_status", "status check")
    engine.record_interaction("get_system_status", "status check 2")
    
    summary = engine.get_status_summary()
    assert summary["routines_count"] == 1
    rec = summary["recommended_routines"][0]
    assert rec["routine_type"] == "daily_system_check"
    assert rec["command"] == "get_system_status"
    assert rec["accepted"] is False
    assert "Saya perasan" in rec["recommendation_message"] # Malay syntax

def test_custom_command_recommendation():
    engine = AdaptiveRoutineEngine(repeat_threshold=1)
    
    engine.record_interaction("custom_action", "do custom")
    summary = engine.get_status_summary()
    assert summary["routines_count"] == 1
    rec = summary["recommended_routines"][0]
    assert rec["routine_type"] == "automate_custom_action"
    assert rec["command"] == "custom_action"

def test_accept_routine():
    engine = AdaptiveRoutineEngine(repeat_threshold=1)
    engine.record_interaction("open_dashboard", "buka hmi")
    
    # Verify accept works
    success = engine.accept_routine("anomaly_dashboard_popup")
    assert success is True
    
    summary = engine.get_status_summary()
    assert summary["recommended_routines"][0]["accepted"] is True
    
    # Accept invalid routine
    success_none = engine.accept_routine("invalid_routine")
    assert success_none is False
