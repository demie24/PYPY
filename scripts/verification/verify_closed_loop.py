#!/usr/bin/env python3
"""Reproducible stateful verification of the default cyber-physical chain."""

import argparse
import json
import math
import threading
import time

from core.mqtt_compat import create_client


TOPICS = (
    "pypy/grid/telemetry", "grid/alerts", "grid/threat",
    "grid/control/proposed", "grid/orchestrator/events", "grid/control",
    "grid/events",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1884)
    parser.add_argument("--calibration-seconds", type=float, default=22.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    messages = []
    lock = threading.Lock()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            raise RuntimeError(f"MQTT connection failed: {reason_code}")
        for topic in TOPICS:
            client.subscribe(topic)

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        with lock:
            messages.append((message.topic, payload))

    def wait_for(topic, predicate, label):
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            with lock:
                matches = [payload for candidate, payload in messages if candidate == topic]
            result = next((payload for payload in reversed(matches) if predicate(payload)), None)
            if result is not None:
                evidence = {
                    key: result[key]
                    for key in (
                        "timestamp", "type", "severity", "suspect_node",
                        "threat_score", "command", "target", "event", "reason",
                    )
                    if key in result
                }
                if topic == "pypy/grid/telemetry":
                    state = result.get("state", {})
                    evidence.update({
                        "grid_name": result.get("grid_name"),
                        "active_attack": result.get("attack_status", {}).get("active_attack"),
                        "L_line_0": state.get("breakers", {}).get("L_line_0"),
                        "L_line_1": state.get("breakers", {}).get("L_line_1"),
                        "Bus_1_voltage": state.get("buses", {}).get("Bus_1", {}).get("voltage_pu"),
                    })
                print(json.dumps({"checkpoint": label, "topic": topic, "evidence": evidence}, default=str))
                return result
            time.sleep(0.2)
        raise TimeoutError(f"Timed out waiting for {label} on {topic}")

    client = create_client("pypy_repository_closed_loop_verifier")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    try:
        time.sleep(args.calibration_seconds)
        client.publish("grid/attack", json.dumps({"action": "STOP"}))
        client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
        nominal = wait_for(
            "pypy/grid/telemetry",
            lambda p: p.get("grid_name") == "ieee39"
            and p.get("attack_status", {}).get("active_attack") is None
            and not [state for state in p.get("state", {}).get("breakers", {}).values() if state != "CLOSED"],
            "nominal_before",
        )
        before_voltage = nominal["state"]["buses"]["Bus_1"]["voltage_pu"]

        with lock:
            messages.clear()
        client.publish("grid/attack", json.dumps({
            "action": "START", "type": "FDIA",
            "config": {"target": "Bus_5", "bias": -0.35, "scale": 0.7},
        }))
        wait_for("grid/alerts", lambda p: p.get("type") == "TARGETED_FDIA", "ai_detection")
        wait_for("grid/threat", lambda p: p.get("threat_score", 0) > 0, "threat_assessment")

        # Allow the threat context to mature before adding genuine physical evidence.
        time.sleep(10.5)
        for target in ("L_line_0", "L_line_1"):
            client.publish("grid/attack", json.dumps({
                "action": "START", "type": "BREAKER_MANIPULATION",
                "config": {"target": target, "command": "OPEN"},
            }))
            time.sleep(1.2)
        wait_for(
            "pypy/grid/telemetry",
            lambda p: all(p.get("state", {}).get("breakers", {}).get(line) == "OPEN" for line in ("L_line_0", "L_line_1")),
            "physical_isolation",
        )
        client.publish("grid/attack", json.dumps({"action": "STOP"}))

        proposal = wait_for(
            "grid/control/proposed",
            lambda p: p.get("command") == "CLOSE" and p.get("target") in ("L_line_0", "L_line_1"),
            "recovery_proposal",
        )
        decision = wait_for(
            "grid/orchestrator/events",
            lambda p: p.get("target") == proposal["target"],
            "orchestrator_decision",
        )
        if decision.get("event") != "APPROVAL":
            raise RuntimeError(f"Recovery was not approved: {decision}")
        restored = wait_for(
            "pypy/grid/telemetry",
            lambda p: p.get("state", {}).get("breakers", {}).get(proposal["target"]) == "CLOSED"
            and math.isfinite(float(p.get("state", {}).get("buses", {}).get("Bus_1", {}).get("voltage_pu", math.nan))),
            "digital_twin_state_change",
        )
        after_voltage = restored["state"]["buses"]["Bus_1"]["voltage_pu"]
        print(json.dumps({
            "result": "PASS", "grid": "ieee39", "recovered_breaker": proposal["target"],
            "bus_1_voltage_before": before_voltage, "bus_1_voltage_after": after_voltage,
        }))
        return 0
    finally:
        client.publish("grid/attack", json.dumps({"action": "STOP"}))
        time.sleep(1.5)
        # Repeat after a telemetry cycle so a queued manipulation frame cannot
        # race the cleanup close command.
        for _ in range(2):
            for target in ("L_line_0", "L_line_1"):
                client.publish("grid/control", json.dumps({
                    "command": "CLOSE", "target": target, "source": "VERIFICATION_CLEANUP",
                }))
            client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
            time.sleep(2)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
