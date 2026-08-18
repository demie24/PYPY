import math

from core.ai_detection.detector import NumPyAutoencoderDetector


def telemetry(value=1.0):
    return {"state": {"buses": {f"Bus_{i}": {"voltage_pu": value} for i in range(1, 40)}}}


def test_runtime_detector_covers_all_39_buses():
    detector = NumPyAutoencoderDetector(input_dim=39, hidden_dim=16)
    detector.calibration_frames = 1
    result = detector.process_telemetry(telemetry())
    assert len(result["voltages"]) == 39
    frame = telemetry()
    frame["state"]["buses"]["Bus_39"]["voltage_pu"] = 0.5
    changed = detector.process_telemetry(frame)
    assert len(changed["reconstruction"]) == 39
    assert changed["loss"] > 0


def test_non_convergence_never_emits_nan_loss():
    detector = NumPyAutoencoderDetector(input_dim=39, hidden_dim=16)
    frame = telemetry()
    frame["state"]["buses"]["Bus_25"]["voltage_pu"] = float("nan")
    result = detector.process_telemetry(frame)
    assert result["non_converged"] is True
    assert math.isfinite(result["loss"])
