import pytest

from core.ai_runtime.fusion_service import CalibratedFusionEngine


def telemetry(attack=None):
    return {
        "timestamp": 123,
        "attack_status": {"active_attack": attack},
        "solver_status": {"converged": True},
        "state": {"breakers": {"L_line_0": "CLOSED"}},
    }


def model_payloads(offset=0.0):
    return {
        "lstm": {"anomaly_score": 0.99 + offset},
        "gnn": {"anomaly_score": 0.98 + offset},
        "stgnn": {"max_future_node_risk": 0.55 + offset},
        "pinn": {"physics_loss": 12.0 + offset * 10},
    }


def calibrate(engine):
    engine.set_telemetry(telemetry())
    for tick in range(engine.calibration_samples):
        for name, payload in model_payloads().items():
            engine.ingest(name, payload, now=float(tick))


def test_nominal_checkpoint_bias_is_calibrated_not_treated_as_attack():
    engine = CalibratedFusionEngine(calibration_samples=5, freshness_seconds=5)
    calibrate(engine)
    result = engine.fuse(now=4.0)
    assert result["calibrated"] is True
    assert result["fused_risk"] == pytest.approx(0.0)


def test_attack_drift_raises_risk_and_does_not_poison_baseline():
    engine = CalibratedFusionEngine(calibration_samples=5, freshness_seconds=5)
    calibrate(engine)
    counts = {name: len(values) for name, values in engine.baselines.items()}
    engine.set_telemetry(telemetry("FDIA"))
    for name, payload in model_payloads(offset=0.25).items():
        engine.ingest(name, payload, now=5.0)
    result = engine.fuse(now=5.0)
    assert result["fused_risk"] > 0.95
    assert counts == {name: len(values) for name, values in engine.baselines.items()}


def test_missing_or_stale_model_blocks_fusion():
    engine = CalibratedFusionEngine(calibration_samples=2, freshness_seconds=1)
    calibrate(engine)
    assert engine.fuse(now=10.0) is None


def test_non_finite_input_is_rejected():
    engine = CalibratedFusionEngine(calibration_samples=2)
    engine.set_telemetry(telemetry())
    with pytest.raises(ValueError, match="non-finite"):
        engine.ingest("pinn", {"physics_loss": float("nan")})
