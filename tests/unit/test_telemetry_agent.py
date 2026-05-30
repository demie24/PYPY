import pytest
from core.assistant.telemetry_agent import TelemetryAgent

def test_telemetry_agent_initial_state():
    agent = TelemetryAgent()
    summary = agent.get_status_summary()
    assert summary["agent_name"] == "TelemetryAgent"
    assert summary["status"] == "NOMINAL"
    assert summary["confidence_score"] == 1.0
    assert not summary["anomalies"]
    assert not summary["priority_events"]
    assert not summary["cascade_alerts"]
    assert not summary["drift_summary"]

def test_telemetry_agent_voltage_anomalies():
    agent = TelemetryAgent()
    # Test nominal voltage
    agent.analyze_telemetry({"bus_1_v": 1.0}, {})
    assert agent.status == "NOMINAL"
    
    # Test medium deviation
    agent.analyze_telemetry({"bus_1_v": 1.06}, {})
    assert agent.status == "DEGRADED"
    assert len(agent.detected_anomalies) == 1
    assert agent.detected_anomalies[0]["severity"] == "MEDIUM"
    assert "melencong sikit" in agent.detected_anomalies[0]["description"]
    
    # Test high deviation
    agent.analyze_telemetry({"bus_1_v": 1.12}, {})
    assert agent.status == "HIGH_ANOMALY"
    assert agent.detected_anomalies[0]["severity"] == "HIGH"
    
    # Test critical deviation
    agent.analyze_telemetry({"bus_1_v": 0.82}, {})
    assert agent.status == "CRITICAL_ANOMALY"
    assert agent.detected_anomalies[0]["severity"] == "CRITICAL"
    assert "tahap kritikal" in agent.detected_anomalies[0]["description"]

def test_telemetry_agent_line_load_anomalies():
    agent = TelemetryAgent()
    # Test critical line overload
    agent.analyze_telemetry({"line_L1_2_load": 115.0}, {})
    assert agent.status == "CRITICAL_ANOMALY"
    assert len(agent.detected_anomalies) == 1
    assert agent.detected_anomalies[0]["severity"] == "CRITICAL"
    assert "beban kritikal" in agent.detected_anomalies[0]["description"]

def test_telemetry_agent_drift_storm():
    agent = TelemetryAgent()
    # Test nominal drift
    sync_states = {
        "node_sync_states": {
            "esp32_zone1": {"drift_sec": 0.01},
            "esp32_zone2": {"drift_sec": 0.02}
        }
    }
    agent.analyze_telemetry({}, sync_states)
    assert not agent.drift_summary["is_drift_storm"]
    
    # Test drift storm (3 or more nodes skew > 25ms)
    sync_states = {
        "node_sync_states": {
            "esp32_zone1": {"drift_sec": 0.03},
            "esp32_zone2": {"drift_sec": 0.04},
            "esp32_zone3": {"drift_sec": 0.05}
        }
    }
    agent.analyze_telemetry({}, sync_states)
    assert agent.status == "CRITICAL_ANOMALY"
    assert agent.drift_summary["is_drift_storm"]
    assert agent.drift_summary["skewed_count"] == 3

def test_telemetry_agent_priority_events():
    agent = TelemetryAgent()
    # medium voltage dev + critical line load
    agent.analyze_telemetry({"bus_1_v": 1.06, "line_L1_2_load": 115.0}, {})
    # Priority events should sort CRITICAL before MEDIUM
    assert len(agent.priority_events) == 2
    assert agent.priority_events[0]["severity"] == "CRITICAL"
    assert agent.priority_events[1]["severity"] == "MEDIUM"

def test_telemetry_agent_cascading_failures():
    agent = TelemetryAgent()
    # Initialize load and breaker state
    agent.analyze_telemetry({"breaker_1": 1.0, "line_L2_3_load": 40.0}, {})
    
    # Trigger transition breaker OPEN and load spike (>15% increase)
    agent.analyze_telemetry({"breaker_1": 0.0, "line_L2_3_load": 65.0}, {})
    assert len(agent.cascade_alerts) == 1
    assert agent.cascade_alerts[0]["cause_breaker"] == "1"
    assert agent.cascade_alerts[0]["effect_line"] == "line_L2_3_load"
    assert "Cascade dikesan" in agent.cascade_alerts[0]["description"]

def test_telemetry_agent_reset():
    agent = TelemetryAgent()
    agent.analyze_telemetry({"bus_1_v": 0.82}, {})
    assert agent.status == "CRITICAL_ANOMALY"
    
    agent.reset_agent()
    assert agent.status == "NOMINAL"
    assert not agent.voltage_history
    assert not agent.detected_anomalies
