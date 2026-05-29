import pytest
import time
from core.assistant.proactive_assistant_engine import ProactiveAssistantEngine

def test_proactive_confidence_threshold_rejection():
    engine = ProactiveAssistantEngine()
    
    # Setup mock grid state with low confidence (< 0.50)
    grid_state = {
        "threat": {"threat_score": 10.0, "confidence": 0.40},
        "comms_online": False
    }
    hardware_state = {}
    
    alert = engine.scan_grid_state(grid_state, hardware_state)
    assert alert is None

def test_proactive_alert_triggers_malay_messages():
    engine = ProactiveAssistantEngine()
    
    # 1. Comms offline -> broker_disconnect
    grid_state = {
        "threat": {"threat_score": 10.0, "confidence": 0.80},
        "comms_online": False
    }
    alert = engine.scan_grid_state(grid_state, {})
    assert alert is not None
    assert alert["category"] == "broker_disconnect"
    assert alert["message"] == "baby, MQTT broker disconnected"
    assert alert["is_minor"] is False

    # Reset cooldowns to test other categories
    engine.reset_cooldowns()

    # 2. Relay unstable -> relay_unstable
    grid_state = {
        "threat": {"threat_score": 15.0, "confidence": 0.80},
        "relay_unstable": True
    }
    alert = engine.scan_grid_state(grid_state, {})
    assert alert is not None
    assert alert["category"] == "relay_unstable"
    assert alert["message"] == "sistem relay nampak unstable"
    assert alert["is_minor"] is False

    engine.reset_cooldowns()

    # 3. Sync recovered -> sync_recovered
    grid_state = {
        "threat": {"threat_score": 12.0, "confidence": 0.80},
        "sync_recovered": True
    }
    alert = engine.scan_grid_state(grid_state, {})
    assert alert is not None
    assert alert["category"] == "sync_recovered"
    assert alert["message"] == "telemetry synchronization dah recover"
    assert alert["is_minor"] is True

    engine.reset_cooldowns()

    # 4. Latency spike -> latency_spike
    grid_state = {
        "threat": {"threat_score": 5.0, "confidence": 0.80}
    }
    hardware_state = {"latency_ms": 550.0}
    alert = engine.scan_grid_state(grid_state, hardware_state)
    assert alert is not None
    assert alert["category"] == "latency_spike"
    assert alert["message"] == "saya detect latency spike pada edge node"
    assert alert["is_minor"] is True

def test_cooldown_lockout_period():
    engine = ProactiveAssistantEngine(cooldown_period=1.0)
    
    grid_state = {
        "threat": {"threat_score": 20.0, "confidence": 0.90},
        "comms_online": False
    }
    
    # First alert triggers
    alert1 = engine.scan_grid_state(grid_state, {})
    assert alert1 is not None
    
    # Immediate second alert gets blocked by cooldown
    alert2 = engine.scan_grid_state(grid_state, {})
    assert alert2 is None
    assert engine.get_remaining_cooldown("broker_disconnect") > 0.0
    
    # Wait for cooldown to expire
    time.sleep(1.1)
    alert3 = engine.scan_grid_state(grid_state, {})
    assert alert3 is not None

def test_critical_grid_threat_override():
    # Threat score > 70.0 suppresses minor alerts but allows major ones
    engine = ProactiveAssistantEngine()
    
    # Minor alert: latency spike
    grid_state = {
        "threat": {"threat_score": 75.0, "confidence": 0.95}
    }
    hardware_state = {"latency_ms": 600.0}
    
    # Latency spike is minor (is_minor = True) -> suppressed under critical threat
    alert = engine.scan_grid_state(grid_state, hardware_state)
    assert alert is None
    
    # Major alert: Broker disconnect is major (is_minor = False) -> not suppressed
    grid_state["comms_online"] = False
    alert = engine.scan_grid_state(grid_state, hardware_state)
    assert alert is not None
    assert alert["category"] == "broker_disconnect"
