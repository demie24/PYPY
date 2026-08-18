from types import SimpleNamespace

from core.physics_validation.kcl_validator import KCLValidator
from core.physics_validation.kvl_validator import KVLValidator


TOPOLOGY = SimpleNamespace(
    num_buses=2,
    generators={0: {}},
    loads={1: {}},
    lines=[{"id": "L_line_0", "from": 0, "to": 1, "X": 10.0}],
)


def frame(flow=10.0, attack=None):
    return {
        "attack_status": {"active_attack": attack},
        "solver_status": {"converged": True},
        "state": {
            "buses": {
                "Bus_1": {"P_mw": -10.0, "Q_mvar": 0.0, "voltage_pu": 1.0, "angle_rad": 0.1},
                "Bus_2": {"P_mw": 10.0, "Q_mvar": 0.0, "voltage_pu": 0.99, "angle_rad": 0.0},
            },
            "lines": {"L_line_0": {"P_mw": flow, "Q_mvar": 0.0, "current_pu": 0.1}},
            "breakers": {"L_line_0": "CLOSED"},
        },
    }


def test_ieee_residuals_calibrate_nominal_and_freeze_during_attack():
    kcl = KCLValidator(TOPOLOGY)
    kvl = KVLValidator(TOPOLOGY)
    for _ in range(15):
        assert kcl.validate(frame())["total_mismatch_val"] == 0
        assert kvl.validate(frame())["total_mismatch_val"] == 0

    kcl_attack = kcl.validate(frame(flow=30.0, attack="FDIA"))
    kvl_attack = kvl.validate(frame(flow=30.0, attack="FDIA"))
    assert kcl_attack["total_mismatch_val"] > 0
    assert kvl_attack["total_mismatch_val"] > 0
    assert len(kcl.residual_history["Bus_1"]) == 15
    assert len(kvl.residual_history["L_line_0"]) == 15
