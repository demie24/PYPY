import json
from pathlib import Path


def test_verified_mqtt_contract_is_machine_readable_and_complete():
    schema_path = Path(__file__).parents[2] / "docs" / "mqtt-contract.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    expected_topics = {
        "pypy/grid/telemetry",
        "grid/alerts",
        "grid/threat",
        "grid/control/proposed",
        "grid/orchestrator/events",
        "grid/control",
        "grid/events",
    }
    assert expected_topics.issubset(schema["x-topic-map"])
    for reference in schema["x-topic-map"].values():
        definition = reference.rsplit("/", 1)[-1]
        assert definition in schema["$defs"]
        assert schema["$defs"][definition]["required"]

    telemetry = schema["$defs"]["telemetry"]
    assert "solver_status" in telemetry["required"]
    assert telemetry["properties"]["solver_status"]["$ref"] == "#/$defs/solverStatus"
    assert schema["$defs"]["solverStatus"]["required"] == ["converged", "mode", "iterations"]
    for component in ("lstm", "gnn", "stgnn", "pinn"):
        assert schema["x-topic-map"][f"grid/ai/{component}"] == "#/$defs/modelInference"
        assert schema["x-topic-map"][f"grid/ai/status/{component}"] == "#/$defs/modelStatus"
    assert schema["x-topic-map"]["grid/ai/fusion"] == "#/$defs/aiFusion"
    assert schema["x-topic-map"]["grid/trust_scores"] == "#/$defs/trustScores"
    for component in ("fusion", "trust"):
        assert schema["x-topic-map"][f"grid/ai/status/{component}"] == "#/$defs/modelStatus"
    assert schema["x-topic-map"]["grid/ai/recovery_policy"] == "#/$defs/recoveryPolicy"
    assert schema["x-topic-map"]["grid/ai/status/recovery_policy"] == "#/$defs/modelStatus"
