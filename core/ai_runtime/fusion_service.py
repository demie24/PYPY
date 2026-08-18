"""Calibrated fusion of the four IEEE-39 model-runtime outputs."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from core.ai_runtime.readiness import ModelReadiness
from core.mqtt_compat import create_client


LOGGER = logging.getLogger("ai_runtime.fusion")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "pypy/grid/telemetry")
COMPONENTS = ("lstm", "gnn", "stgnn", "pinn")


class CalibratedFusionEngine:
    """Convert checkpoint-specific raw scores into comparable drift evidence."""

    def __init__(self, calibration_samples: int = 20, freshness_seconds: float = 5.0):
        self.calibration_samples = calibration_samples
        self.freshness_seconds = freshness_seconds
        self.baselines = {name: deque(maxlen=200) for name in COMPONENTS}
        self.latest: dict[str, tuple[float, dict[str, Any]]] = {}
        self.latest_telemetry: dict[str, Any] | None = None

    @property
    def calibrated(self) -> bool:
        return all(len(values) >= self.calibration_samples for values in self.baselines.values())

    @staticmethod
    def scalar(component: str, payload: dict[str, Any]) -> float:
        fields = {
            "lstm": "anomaly_score",
            "gnn": "anomaly_score",
            "stgnn": "max_future_node_risk",
            "pinn": "physics_loss",
        }
        value = float(payload[fields[component]])
        if not math.isfinite(value):
            raise ValueError(f"non-finite {component} fusion input")
        return value

    def set_telemetry(self, payload: dict[str, Any]) -> None:
        self.latest_telemetry = payload

    def _nominal_frame(self) -> bool:
        if not self.latest_telemetry:
            return False
        attack = (self.latest_telemetry.get("attack_status") or {}).get("active_attack")
        solver = self.latest_telemetry.get("solver_status") or {}
        breakers = self.latest_telemetry.get("state", {}).get("breakers", {})
        return (
            not attack
            and solver.get("converged", True) is True
            and all(status == "CLOSED" for status in breakers.values())
        )

    def ingest(self, component: str, payload: dict[str, Any], now: float | None = None) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"unsupported fusion component: {component}")
        received = time.time() if now is None else now
        value = self.scalar(component, payload)
        self.latest[component] = (received, payload)
        if self._nominal_frame():
            self.baselines[component].append(value)

    def fuse(self, now: float | None = None) -> dict[str, Any] | None:
        current = time.time() if now is None else now
        if not self.calibrated or set(self.latest) != set(COMPONENTS):
            return None
        ages = {name: current - self.latest[name][0] for name in COMPONENTS}
        if any(age > self.freshness_seconds or age < 0 for age in ages.values()):
            return None

        evidence: dict[str, float] = {}
        raw: dict[str, float] = {}
        baseline: dict[str, dict[str, float]] = {}
        for name in COMPONENTS:
            value = self.scalar(name, self.latest[name][1])
            samples = np.asarray(self.baselines[name], dtype=float)
            median = float(np.median(samples))
            mad = float(np.median(np.abs(samples - median)))
            scale = max(1.4826 * mad, abs(median) * 0.01, 1e-6)
            # Both unusually high and unusually low outputs are distribution
            # drift. This avoids pretending uncalibrated checkpoint logits are
            # probabilities with a shared semantic threshold.
            z_score = abs(value - median) / scale
            evidence[name] = float(1.0 - math.exp(-z_score / 3.0))
            raw[name] = value
            baseline[name] = {"median": median, "robust_scale": scale, "samples": len(samples)}

        weights = {"lstm": 0.30, "gnn": 0.25, "stgnn": 0.20, "pinn": 0.25}
        fused_risk = sum(weights[name] * evidence[name] for name in COMPONENTS)
        agreement = 1.0 - float(np.std(list(evidence.values())))
        return {
            "timestamp": int(current * 1000),
            "source_telemetry_timestamp": (self.latest_telemetry or {}).get("timestamp"),
            "component": "fusion",
            "calibrated": True,
            "calibration_policy": "nominal-converged-all-breakers-closed",
            "fused_risk": round(float(fused_risk), 6),
            "confidence": round(max(0.0, min(1.0, agreement)), 6),
            "component_evidence": evidence,
            "raw_model_outputs": raw,
            "baselines": baseline,
            "input_age_seconds": ages,
        }


class MQTTFusionService:
    def __init__(self):
        self.engine = CalibratedFusionEngine(
            calibration_samples=int(os.getenv("FUSION_CALIBRATION_SAMPLES", "20")),
            freshness_seconds=float(os.getenv("FUSION_FRESHNESS_SECONDS", "5")),
        )
        self.readiness = ModelReadiness(
            "fusion", model_loaded=True, checkpoint="calibrated-evidence-fusion-v1"
        )
        self.heartbeat_path = Path("/tmp/pypy_fusion_heartbeat.json")
        self.client = create_client("pypy_ai_fusion")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            client.subscribe(TELEMETRY_TOPIC)
            for component in COMPONENTS:
                client.subscribe(f"grid/ai/{component}")
            LOGGER.info("Fusion subscribed to IEEE-39 telemetry and four model outputs")

    def on_message(self, client, userdata, message):
        accepted_input = False
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if message.topic == TELEMETRY_TOPIC:
                self.engine.set_telemetry(payload)
                self.readiness.record_telemetry()
                accepted_input = True
            else:
                component = message.topic.rsplit("/", 1)[-1]
                if component in COMPONENTS:
                    self.engine.ingest(component, payload)
                    accepted_input = True
            result = self.engine.fuse() if accepted_input else None
            if result is not None:
                client.publish("grid/ai/fusion", json.dumps(result, allow_nan=False))
                self.readiness.record_inference()
        except Exception as exc:
            self.readiness.record_error(exc)
            LOGGER.warning("Fusion input rejected on %s: %s", message.topic, exc)
        finally:
            self.publish_status(client)

    def publish_status(self, client):
        status = self.readiness.snapshot(stale_after=15.0)
        status["calibrated"] = self.engine.calibrated
        status["calibration_counts"] = {
            name: len(values) for name, values in self.engine.baselines.items()
        }
        encoded = json.dumps(status, allow_nan=False)
        self.heartbeat_path.write_text(encoded, encoding="utf-8")
        client.publish("grid/ai/status/fusion", encoded, retain=True)

    def run(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.client.loop_forever()


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(message)s")
    MQTTFusionService().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
