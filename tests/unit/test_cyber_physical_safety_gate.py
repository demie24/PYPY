import time

from core.orchestrator.ai_orchestrator import AIOrchestrator


def telemetry(*, target_state="OPEN", outage=True):
    return {
        "timestamp": int(time.time() * 1000),
        "attack_status": {"active_attack": "FDIA"},
        "state": {
            "breakers": {"L_line_1": target_state},
            "buses": {
                "Bus_1": {"voltage_pu": 1.0, "frequency_hz": 60.0},
                "Bus_2": {"voltage_pu": float("nan") if outage else 1.0, "frequency_hz": 60.0},
            },
            "lines": {},
        },
    }


def prepare(threat=None, **telemetry_options):
    orchestrator = AIOrchestrator()
    orchestrator.update_state("pypy/grid/telemetry", telemetry(**telemetry_options))
    if threat is not None:
        orchestrator.update_state("grid/threat", threat)
    return orchestrator


def test_ai_context_without_physical_outage_cannot_authorize_recovery():
    orchestrator = prepare(
        {"timestamp": int(time.time() * 1000), "threat_score": 100},
        outage=False,
    )
    approved, reason = orchestrator.evaluate_proposed_command(
        "CLOSE", "L_line_1", "L6_RECOVERY_FULL"
    )
    assert not approved
    assert "physical outage" in reason


def test_l6_recovery_requires_threat_context():
    orchestrator = prepare()
    approved, reason = orchestrator.evaluate_proposed_command(
        "CLOSE", "L_line_1", "L6_RECOVERY_FULL"
    )
    assert not approved
    assert "fresh threat" in reason


def test_l6_recovery_rejects_stale_threat_context():
    orchestrator = prepare({"timestamp": int((time.time() - 31) * 1000), "threat_score": 100})
    approved, reason = orchestrator.evaluate_proposed_command(
        "CLOSE", "L_line_1", "L6_RECOVERY_FULL"
    )
    assert not approved
    assert "fresh threat" in reason


def test_l6_recovery_requires_target_to_be_physically_open():
    orchestrator = prepare(
        {"timestamp": int(time.time() * 1000), "threat_score": 100},
        target_state="CLOSED",
    )
    approved, reason = orchestrator.evaluate_proposed_command(
        "CLOSE", "L_line_1", "L6_RECOVERY_FULL"
    )
    assert not approved
    assert "open target" in reason


def test_duplicate_breaker_actions_are_guarded():
    orchestrator = prepare(
        {"timestamp": int(time.time() * 1000), "threat_score": 100}
    )
    first, _ = orchestrator.evaluate_proposed_command(
        "CLOSE", "L_line_1", "L6_RECOVERY_FULL"
    )
    second, reason = orchestrator.evaluate_proposed_command(
        "CLOSE", "L_line_1", "L6_RECOVERY_FULL"
    )
    assert first
    assert not second
    assert "guard delay" in reason
