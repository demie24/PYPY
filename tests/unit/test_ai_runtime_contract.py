import math

import pytest

from core.ai_runtime.features import TelemetryFeatureError, extract_ieee39_features
from core.ai_runtime.readiness import ModelReadiness


def _telemetry():
    buses = {
        f"Bus_{i}": {
            "P_mw": float(i),
            "Q_mvar": float(-i),
            "voltage_pu": 1.0 + i / 10000.0,
            "angle_rad": i / 1000.0,
        }
        for i in range(1, 40)
    }
    branch_ids = [f"L_line_{i}" for i in range(35)] + [f"L_trafo_{i}" for i in range(11)]
    lines = {
        branch_id: {"P_mw": i, "Q_mvar": -i, "capacity_pct": 20.0 + i}
        for i, branch_id in enumerate(branch_ids)
    }
    return {
        "timestamp": 1_700_000_000_000,
        "grid_name": "ieee39",
        "solver_status": {"converged": True, "mode": "converged", "iterations": 4},
        "state": {
            "buses": buses,
            "lines": lines,
            "breakers": {branch_id: "CLOSED" for branch_id in branch_ids},
        },
    }


def test_ieee39_feature_contract_has_model_training_shapes_and_units():
    frame = extract_ieee39_features(_telemetry())

    assert frame.temporal.shape == (156,)
    assert frame.nodes.shape == (39, 4)
    assert frame.edges.shape == (46, 5)
    assert frame.temporal[0] == pytest.approx(1.0)  # LSTM P is stored in MW
    assert frame.nodes[0, 0] == pytest.approx(0.01)  # graph P is per-unit
    assert frame.branch_ids[0] == "L_line_0"
    assert frame.branch_ids[-1] == "L_trafo_10"


def test_ieee39_feature_contract_rejects_non_finite_values():
    telemetry = _telemetry()
    telemetry["state"]["buses"]["Bus_17"]["voltage_pu"] = math.nan

    with pytest.raises(TelemetryFeatureError, match="non_finite_telemetry") as exc:
        extract_ieee39_features(telemetry)
    assert exc.value.reason == "non_finite_telemetry"


def test_ieee39_feature_contract_rejects_non_converged_power_flow():
    telemetry = _telemetry()
    telemetry["solver_status"] = {"converged": False, "mode": "failed"}

    with pytest.raises(TelemetryFeatureError, match="power_flow_non_convergence"):
        extract_ieee39_features(telemetry)


def test_model_readiness_requires_loaded_model_and_fresh_successful_inference():
    readiness = ModelReadiness("lstm", model_loaded=True, checkpoint="model.pt", started_at=90.0)
    readiness.record_telemetry(99.0)
    readiness.record_inference(99.5)

    assert readiness.snapshot(now=100.0, stale_after=2.0)["ready"] is True
    assert readiness.snapshot(now=103.0, stale_after=2.0)["ready"] is False
    readiness.record_error("non-finite output")
    assert readiness.snapshot(now=100.0, stale_after=2.0)["ready"] is False
