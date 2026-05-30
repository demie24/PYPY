import pytest
import time
from core.assistant.relay_health_monitor import RelayHealthMonitor

def test_relay_health_monitor_initialization():
    monitor = RelayHealthMonitor()
    assert "L1_4" in monitor.breakers
    assert monitor.breakers["L1_4"]["wear_pct"] == 0.0
    assert monitor.breakers["L1_4"]["switch_count"] == 0
    assert monitor.breakers["L1_4"]["unstable"] is False

def test_update_relay_state_wear():
    monitor = RelayHealthMonitor()
    
    # Update breaker state to CLOSED (should be no transition if it was CLOSED already)
    monitor.update_relay_state("L1_4", "CLOSED")
    assert monitor.breakers["L1_4"]["switch_count"] == 0
    assert monitor.breakers["L1_4"]["wear_pct"] == 0.0

    # Transition to OPEN
    monitor.update_relay_state("L1_4", "OPEN")
    assert monitor.breakers["L1_4"]["switch_count"] == 1
    assert monitor.breakers["L1_4"]["wear_pct"] == 0.5

    # Transition back to CLOSED
    monitor.update_relay_state("L1_4", "CLOSED")
    assert monitor.breakers["L1_4"]["switch_count"] == 2
    assert monitor.breakers["L1_4"]["wear_pct"] == 1.0

def test_oscillation_chattering_detection():
    monitor = RelayHealthMonitor()
    
    now = time.time()
    # 4 transitions quickly
    monitor.breakers["L1_4"]["state"] = "CLOSED"
    monitor.breakers["L1_4"]["last_transitions"] = [now - 25, now - 20, now - 15]
    monitor.breakers["L1_4"]["state"] = "OPEN" # 4th transition
    monitor.update_relay_state("L1_4", "CLOSED") # 5th transition
    
    assert monitor.breakers["L1_4"]["unstable"] is True

    # Test pruning of old transitions
    # Set transitions older than 30s
    monitor.breakers["L1_4"]["last_transitions"] = [now - 40, now - 35, now - 5]
    monitor.update_relay_state("L1_4", "CLOSED") # transition state remains same, no state change, but oscillation is evaluated
    # should prune elements older than 30s
    monitor.breakers["L1_4"]["state"] = "OPEN"
    monitor.update_relay_state("L1_4", "CLOSED")
    assert monitor.breakers["L1_4"]["unstable"] is False

def test_recovery_recommendations():
    monitor = RelayHealthMonitor()
    
    # 1. Healthy breaker should return no recommendations
    assert not monitor.get_recovery_recommendations("L1_4")

    # 2. Critical chattering/oscillation lockout recommendations (Malay)
    monitor.breakers["L1_4"]["unstable"] = True
    
    # With confidence score >= 0.75
    recs = monitor.get_recovery_recommendations("L1_4", confidence_score=0.80)
    assert len(recs) == 1
    assert recs[0]["action"] == "LOCKOUT_BREAKER"
    assert "lock" in recs[0]["suggestion"]
    
    # With confidence score < 0.75
    recs = monitor.get_recovery_recommendations("L1_4", confidence_score=0.50)
    assert len(recs) == 1
    assert recs[0]["action"] == "LOCKOUT_BREAKER"
    assert recs[0]["severity"] == "BLOCKED"

    # 3. Solenoid calibration recommendations
    monitor.breakers["L1_4"]["unstable"] = False
    monitor.breakers["L1_4"]["timing_ms"] = 130.0
    recs = monitor.get_recovery_recommendations("L1_4", confidence_score=0.80)
    assert len(recs) == 1
    assert recs[0]["action"] == "CALIBRATE_SOLENOID"
    assert "solenoid" in recs[0]["suggestion"]

    # 4. Contact replacement recommendations
    monitor.breakers["L1_4"]["timing_ms"] = 50.0
    monitor.breakers["L1_4"]["wear_pct"] = 85.0
    recs = monitor.get_recovery_recommendations("L1_4")
    assert len(recs) == 1
    assert recs[0]["action"] == "REPLACE_CONTACT"
    assert "wear" in recs[0]["suggestion"] or "Wear" in recs[0]["suggestion"]

def test_get_status_summary_and_reset():
    monitor = RelayHealthMonitor()
    monitor.update_relay_state("L1_4", "OPEN")
    monitor.breakers["L1_4"]["wear_pct"] = 90.0
    monitor.breakers["L1_4"]["unstable"] = True
    
    summary = monitor.get_status_summary()
    assert "L1_4" in summary["unstable_breakers"]
    assert "L1_4" in summary["wear_report"]
    assert len(summary["recommendations"]) > 0

    monitor.reset_engine()
    assert monitor.breakers["L1_4"]["wear_pct"] == 0.0
    assert monitor.breakers["L1_4"]["unstable"] is False
    assert not monitor.breakers["L1_4"]["last_transitions"]
