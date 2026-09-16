from core.self_healing.recovery_policy_service import IEEE39RecoveryEncoder, RecoveryPolicyRuntime


BRANCHES = [f"L_line_{i}" for i in range(35)] + [f"L_trafo_{i}" for i in range(11)]


def telemetry():
    return {
        "grid_name": "ieee39",
        "state": {
            "buses": {
                f"Bus_{i}": {"voltage_pu": 1.0, "angle_rad": 0.0, "P_mw": 0.0, "Q_mvar": 0.0}
                for i in range(1, 40)
            },
            "lines": {
                key: {"P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 0.0} for key in BRANCHES
            },
            "breakers": {key: "CLOSED" for key in BRANCHES},
        },
    }


def test_encoder_covers_last_ieee39_bus_and_branch():
    encoder = IEEE39RecoveryEncoder()
    frame = telemetry()
    baseline = encoder.encode(frame)
    frame["state"]["buses"]["Bus_39"]["voltage_pu"] = 0.5
    frame["state"]["breakers"]["L_trafo_10"] = "OPEN"
    changed = encoder.encode(frame)
    assert changed.shape == (72,)
    assert changed[8] != baseline[8]
    assert changed[44] != baseline[44]


def test_encoder_maps_non_convergence_to_explicit_failure_state_without_nan():
    encoder = IEEE39RecoveryEncoder()
    frame = telemetry()
    frame["solver_status"] = {"converged": False, "mode": "failed"}
    frame["state"]["buses"]["Bus_39"]["voltage_pu"] = float("nan")
    frame["state"]["buses"]["Bus_39"]["angle_rad"] = float("nan")
    vector = encoder.encode(frame)
    assert vector[70] == 1.0
    assert all(value == value for value in vector)


def test_ppo_and_dqn_emit_sandbox_gated_ieee39_recovery_intent():
    runtime = RecoveryPolicyRuntime("checkpoints/ppo_self_healing.pt", "checkpoints/dqn_self_healing.pt")
    runtime.validator.validate_action = lambda *args: {
        "is_safe": True, "violations": [], "safety_score": 1.0,
        "solver_converged": True, "finite_state": True,
        "voltage_safe": True, "thermal_safe": True, "cascade_safe": True,
        "topology_valid": True, "overall_safe": True,
        "cascade_risk": 0.0, "confidence": 1.0,
        "predicted_voltages": [1.0] * 39, "predicted_loadings": {},
    }
    frame = telemetry()
    frame["state"]["breakers"]["L_line_0"] = "OPEN"
    result = runtime.infer(frame)
    assert result["coverage"] == {"buses": 39, "branches": 46, "pooling_bins": 9}
    assert result["retrained_on_ieee39"] is False
    assert result["model_decisions"]["ppo"]["action"] in {"RECONNECT_LINE", "ENABLE_RESTORATION", "REROUTE_FLOW"}
    assert result["model_decisions"]["dqn"]["action"] in {"RECONNECT_LINE", "ENABLE_RESTORATION", "REROUTE_FLOW"}
    assert result["consensus"] is True
    assert result["sandbox"]["is_safe"] is True
