from core.threat_engine.scorer import ThreatScoringEngine


def nominal_telemetry():
    return {
        "state": {
            "buses": {"Bus_1": {"voltage_pu": 1.0}},
            "lines": {"L_line_0": {"capacity_pct": 20.0}},
            "breakers": {"L_line_0": "CLOSED"},
        },
        "attack_status": {"active_attack": None, "compromised_nodes": {}},
    }


def test_calibrated_fusion_and_trust_contribute_bounded_evidence():
    engine = ThreatScoringEngine()
    engine.update_ai_fusion({"calibrated": True, "fused_risk": 0.8})
    engine.update_trust({"bus_trust": {"Bus_1": 50}, "line_trust": {"L_line_0": 50}})
    result = engine.calculate_threat(nominal_telemetry())
    assert result["threat_score"] == 28
    assert result["ai_evidence"]["fusion_used"] is True
    assert result["ai_evidence"]["trust_used"] is True


def test_uncalibrated_fusion_is_not_used_as_threat_evidence():
    engine = ThreatScoringEngine()
    engine.update_ai_fusion({"calibrated": False, "fused_risk": 1.0})
    result = engine.calculate_threat(nominal_telemetry())
    assert result["threat_score"] == 0
    assert result["ai_evidence"]["fusion_used"] is False
