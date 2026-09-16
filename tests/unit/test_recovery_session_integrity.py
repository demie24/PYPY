from core.digital_twin.main import SmartGridDigitalTwin
from core.gateway.store import MemoryStore


def test_consecutive_attacks_get_fresh_correlation_ids(monkeypatch):
    simulator = SmartGridDigitalTwin.__new__(SmartGridDigitalTwin)
    simulator.lock = __import__("threading").RLock()
    simulator.experiment_id = "old-experiment"
    simulator.scenario_id = "old-scenario"
    simulator.last_control_correlation_id = "old-correlation"
    simulator.last_commands = {}
    simulator.attack_rate_limit_bucket = []
    simulator.active_compromises = {}
    simulator.attack_steps = {}
    simulator.breakers = {"L_line_0": "CLOSED"}
    simulator.breaker_cooldowns = {}
    simulator.publisher = type("Publisher", (), {"publish_event": lambda *args, **kwargs: None})()
    monkeypatch.setattr("core.digital_twin.main.time.time", lambda: 1000.0)
    simulator._handle_attack_cmd_unlocked({"action": "START", "type": "BREAKER_MANIPULATION", "config": {"target": "L_line_0", "command": "OPEN"}})
    first = simulator.last_control_correlation_id
    monkeypatch.setattr("core.digital_twin.main.time.time", lambda: 1010.0)
    simulator._handle_attack_cmd_unlocked({"action": "START", "type": "BREAKER_MANIPULATION", "config": {"target": "L_line_0", "command": "OPEN"}})
    assert first != simulator.last_control_correlation_id
    assert simulator.last_control_correlation_id != "old-correlation"
    assert simulator.scenario_id is None


def test_telemetry_does_not_evict_recovery_decisions():
    store = MemoryStore(max_history=4)
    store.add_recovery_evidence("grid/control/proposed", {"target": "L_line_0"})
    store.add_recovery_evidence("grid/orchestrator/events", {"event": "APPROVAL"})
    for timestamp in range(20):
        store.add_recovery_evidence("pypy/grid/telemetry", {"timestamp": timestamp})
    assert [item["topic"] for item in store.recovery_evidence] == [
        "grid/control/proposed", "grid/orchestrator/events", "pypy/grid/telemetry"
    ]
