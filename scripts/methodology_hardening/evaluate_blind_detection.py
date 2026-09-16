#!/usr/bin/env python3
"""Compare telemetry-only and experiment-aware diagnostic behaviour."""

from __future__ import annotations
import copy, json, sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "core"), str(ROOT / "core" / "digital_twin")]
from core.ai_detection.detector import NumPyAutoencoderDetector
from core.digital_twin.main import SmartGridDigitalTwin
from core.threat_engine.scorer import ThreatScoringEngine


def captured_frame(twin):
    holder = {}
    twin.publisher.publish_telemetry = lambda payload: holder.update(payload=copy.deepcopy(payload))
    twin.publisher.publish_ac_telemetry_fields = lambda *args, **kwargs: None
    twin.publisher.publish_event = lambda *args, **kwargs: None
    twin.run_simulation_sweep()
    return holder["payload"]


def confirmation(detector, frames, aware):
    window = []; first = None; raw = []
    size, required = ((detector.attack_window_size, detector.attack_confirm_count) if aware else (detector.window_size, detector.confirm_count))
    for index, frame in enumerate(frames, 1):
        result = detector.process_telemetry(frame); raw.append(result)
        window.append(bool(result["is_anomaly"])); window = window[-size:]
        if first is None and sum(window) >= required: first = index
    return {"detected": first is not None, "first_confirmed_sweep": first,
            "max_loss": max(item["loss"] for item in raw), "final_threshold": detector.threshold}


def evaluate(name, attack):
    twin = SmartGridDigitalTwin(); twin.experiment_id = f"blind-{name.lower()}"; twin.scenario_id = name
    nominal = [captured_frame(twin) for _ in range(25)]
    if name == "REPLAY":
        twin.replay_buffer = copy.deepcopy(nominal[-10:])
    twin.handle_attack_cmd({"action": "START", "type": attack["type"], "config": attack["config"],
                            "experiment_id": twin.experiment_id, "scenario_id": name})
    attacked = [captured_frame(twin) for _ in range(8)]
    blind_detector = NumPyAutoencoderDetector(39); aware_detector = NumPyAutoencoderDetector(39)
    for frame in nominal[:20]: blind_detector.process_telemetry(frame); aware_detector.process_telemetry(frame)
    blind = confirmation(blind_detector, attacked, False); aware = confirmation(aware_detector, attacked, True)
    blind_scores = [ThreatScoringEngine("blind").calculate_threat(frame)["threat_score"] for frame in attacked]
    aware_scores = [ThreatScoringEngine("experiment_aware").calculate_threat(frame)["threat_score"] for frame in attacked]
    return {"blind_autoencoder": blind, "experiment_aware_autoencoder": aware,
            "blind_threat_score_max": max(blind_scores), "experiment_aware_threat_score_max": max(aware_scores),
            "deep_model_input_difference": False,
            "qualification": "Threat comparison excludes separately arriving AI alerts/fusion so it isolates ground-truth metadata contribution."}


def main():
    attacks = {
        "FDIA": {"type": "FDIA", "config": {"target": "Bus_5", "bias": .10, "scale": 1.0}},
        "REPLAY": {"type": "REPLAY", "config": {"target": "Bus_5"}},
        "DOS": {"type": "DOS", "config": {"target": "Bus_5"}},
        "SENSOR_SPOOFING": {"type": "SENSOR_SPOOFING", "config": {"target": "Bus_5", "noise": .08}},
        "BREAKER_MANIPULATION": {"type": "BREAKER_MANIPULATION", "config": {"target": "L_line_0", "command": "OPEN"}},
    }
    results = {name: evaluate(name, attack) for name, attack in attacks.items()}
    report = {"schema_version": "pypy.blind-detection.v1", "mode_definition": {
        "blind": "defence ignores ground-truth attack-control metadata",
        "experiment_aware": "legacy diagnostic mode uses attack metadata for suppression/scoring"}, "results": results,
        "limitations": ["Offline controlled Digital Twin comparison", "No claim that all deep models classify each attack", "Eight post-injection sweeps per case"]}
    out = ROOT / "evaluation/methodology_hardening/blind_detection_report.json"
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(out)


if __name__ == "__main__": main()
