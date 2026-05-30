import pytest
from core.assistant.telemetry_correlation_engine import TelemetryCorrelationEngine

def test_telemetry_correlation_engine_initialization():
    engine = TelemetryCorrelationEngine(window_size=10)
    assert engine.window_size == 10
    assert not engine.history
    assert not engine.correlation_matrix
    assert not engine.cascades

def test_rolling_history_window():
    engine = TelemetryCorrelationEngine(window_size=5)
    for i in range(8):
        engine.add_telemetry_snapshot({"bus_1_v": 1.0 + i * 0.01}, float(i))
    
    assert len(engine.history["bus_1_v"]) == 5
    assert engine.history["bus_1_v"] == [1.03, 1.04, 1.05, 1.06, 1.07]

def test_pearson_correlation_computation():
    engine = TelemetryCorrelationEngine(window_size=10)
    
    # 1. Less than 5 points: returns 0.0
    for i in range(4):
        engine.add_telemetry_snapshot({"bus_1_v": 1.0 + i * 0.01, "bus_1_load": 50.0 + i}, float(i))
    assert engine.correlation_matrix["bus_1_v"]["bus_1_load"] == 0.0
    
    # 2. Perfect linear correlation with >= 5 points
    for i in range(4, 7):
        engine.add_telemetry_snapshot({"bus_1_v": 1.0 + i * 0.01, "bus_1_load": 50.0 + i}, float(i))
    assert abs(engine.correlation_matrix["bus_1_v"]["bus_1_load"] - 1.0) < 0.001

    # 3. Flat/constant values division by zero protection
    engine_flat = TelemetryCorrelationEngine(window_size=10)
    for i in range(6):
        engine_flat.add_telemetry_snapshot({"bus_1_v": 1.0, "bus_1_load": 1.0}, float(i))
    # Both constant
    assert engine_flat.correlation_matrix["bus_1_v"]["bus_1_load"] == 1.0

    # One constant, one varying
    engine_one_flat = TelemetryCorrelationEngine(window_size=10)
    for i in range(6):
        engine_one_flat.add_telemetry_snapshot({"bus_1_v": 1.0, "bus_1_load": float(i)}, float(i))
    assert engine_one_flat.correlation_matrix["bus_1_v"]["bus_1_load"] == 0.0

def test_cascading_events_and_linkage_logs():
    engine = TelemetryCorrelationEngine(window_size=10)
    
    # Simulate a cascade event sequence within 10s:
    # Time 0.0: breaker_1_OPEN
    # Time 2.0: bus_2_v_UNDERVOLTAGE (v < 0.90)
    engine.add_telemetry_snapshot({"breaker_1": 0.0}, 0.0)
    engine.add_telemetry_snapshot({"bus_2_v": 0.85}, 2.0)
    
    summary = engine.get_status_summary()
    assert len(summary["cascades"]) == 1
    assert summary["cascades"][0]["cause"] == "breaker_1_OPEN"
    assert summary["cascades"][0]["effect"] == "bus_2_v_UNDERVOLTAGE"
    assert summary["cascades"][0]["delay_seconds"] == 2.0
    assert summary["cascades"][0]["linkage_score"] == 0.90
    assert len(summary["linkage_logs"]) == 2

    # Verify reset clears cascades
    engine.reset_engine()
    assert not engine.cascades
    assert not engine.history
    assert not engine.correlation_matrix
