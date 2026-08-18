"""MQTT model-serving entrypoint for the trained IEEE-39 AI components."""

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
import torch
import torch.nn.functional as F

from core.ai_runtime.features import TelemetryFeatureError, extract_ieee39_features
from core.ai_runtime.readiness import ModelReadiness
from core.mqtt_compat import create_client


LOGGER = logging.getLogger("ai_runtime.model_service")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "pypy/grid/telemetry")
COMPONENT = os.getenv("MODEL_COMPONENT", "lstm").strip().lower()
SEQUENCE_LENGTH = 20
SUPPORTED_COMPONENTS = {"lstm", "gnn", "stgnn", "pinn"}

OUTPUT_TOPICS = {
    "lstm": "grid/ai/lstm",
    "gnn": "grid/ai/gnn",
    "stgnn": "grid/ai/stgnn",
    "pinn": "grid/ai/pinn",
}

CHECKPOINTS = {
    "lstm": Path("/app/core/lstm/trained_lstm_model.pt"),
    "gnn": Path("/app/core/gnn/trained_gnn_model.pt"),
    "stgnn": Path("/app/core/gnn/trained_stgnn_model.pt"),
    "pinn": Path("/app/core/pinn/trained_pinn_model.pt"),
}


def _ensure_finite(value: Any, field: str = "output") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _ensure_finite(child, f"{field}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _ensure_finite(child, f"{field}[{index}]")
    elif isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        raise ValueError(f"non-finite model output at {field}")


class IEEE39ModelRuntime:
    def __init__(self, component: str = COMPONENT, device: str = "cpu"):
        if component not in SUPPORTED_COMPONENTS:
            raise ValueError(f"Unsupported MODEL_COMPONENT={component!r}")
        self.component = component
        self.device = device
        self.checkpoint = CHECKPOINTS[component]
        self.temporal_frames: deque[np.ndarray] = deque(maxlen=SEQUENCE_LENGTH)
        self.node_frames: deque[np.ndarray] = deque(maxlen=SEQUENCE_LENGTH)
        self.edge_frames: deque[np.ndarray] = deque(maxlen=SEQUENCE_LENGTH)
        self.readiness = ModelReadiness(component, checkpoint=str(self.checkpoint))
        self.model = self._load_model()
        self.readiness.model_loaded = True

    def _load_model(self):
        if not self.checkpoint.is_file():
            raise FileNotFoundError(f"Required {self.component} checkpoint not found: {self.checkpoint}")
        state = torch.load(self.checkpoint, map_location=self.device)

        if self.component == "lstm":
            from core.lstm.lstm_model import IEEE39LSTMClassifier
            model = IEEE39LSTMClassifier(input_dim=156, hidden_dim=64, num_layers=2, num_classes=8, dropout=0.2)
        elif self.component in {"gnn", "stgnn"}:
            from core.digital_twin.grid_topology import GridTopology
            topology = GridTopology(use_legacy_9bus=False)
            # The trained graph models use the Digital Twin's canonical
            # pandapower line-then-transformer order. Runtime inference already
            # receives edge features from the shared pipeline, so importing the
            # offline trainer (and sklearn evaluator) is neither needed nor safe.
            self.edge_index = [(line["from"], line["to"]) for line in topology.lines]
            if len(self.edge_index) != 46 or topology.num_buses != 39:
                raise RuntimeError("Graph checkpoint topology is not IEEE-39/46-branch")
            if self.component == "gnn":
                from core.gnn.gnn_model import IEEE39GNN
                model = IEEE39GNN(edge_index=self.edge_index, hidden_dim=128, num_classes=8)
            else:
                from core.gnn.stgnn_model import IEEE39STGNN
                model = IEEE39STGNN(edge_index=self.edge_index, hidden_dim=64, seq_len=SEQUENCE_LENGTH)
        else:
            from core.pinn.pinn_model import IEEE39PINNAutoencoder
            from core.pinn.physics_loss import IEEE39PhysicsLoss
            model = IEEE39PINNAutoencoder(input_dim=156, hidden_dim=64)
            self.physics_loss = IEEE39PhysicsLoss(device=self.device)

        model.load_state_dict(state)
        model.to(self.device)
        model.eval()
        return model

    def process(self, telemetry: dict[str, Any]) -> dict[str, Any] | None:
        self.readiness.record_telemetry()
        try:
            frame = extract_ieee39_features(telemetry)
            self.temporal_frames.append(frame.temporal)
            self.node_frames.append(frame.nodes)
            self.edge_frames.append(frame.edges)

            if self.component in {"lstm", "stgnn"} and len(self.temporal_frames) < SEQUENCE_LENGTH:
                return None

            started = time.perf_counter()
            with torch.no_grad():
                result = self._infer()
            result.update({
                "timestamp": int(time.time() * 1000),
                "source_telemetry_timestamp": frame.timestamp,
                "component": self.component,
                "model_loaded": True,
                "checkpoint": str(self.checkpoint),
                "inference_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
            })
            _ensure_finite(result)
            self.readiness.record_inference()
            return result
        except Exception as exc:
            self.readiness.record_error(exc)
            raise

    def _infer(self) -> dict[str, Any]:
        if self.component == "lstm":
            sequence = torch.tensor(np.stack(self.temporal_frames), dtype=torch.float32, device=self.device).unsqueeze(0)
            probabilities = F.softmax(self.model(sequence), dim=-1).squeeze(0).cpu().numpy()
            labels = ("NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS")
            predicted = int(np.argmax(probabilities))
            return {
                "classification": labels[predicted],
                "anomaly_score": float(1.0 - probabilities[0]),
                "probabilities": {label: float(probabilities[index]) for index, label in enumerate(labels)},
                "window_size": SEQUENCE_LENGTH,
            }

        if self.component == "gnn":
            nodes = torch.tensor(self.node_frames[-1], dtype=torch.float32, device=self.device).unsqueeze(0)
            edges = torch.tensor(self.edge_frames[-1], dtype=torch.float32, device=self.device).unsqueeze(0)
            logits, node_risk, edge_risk = self.model(nodes, edges)
            probabilities = F.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
            node_values = node_risk.squeeze(0).cpu().numpy()
            edge_values = edge_risk.squeeze(0).cpu().numpy()
            labels = ("NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS")
            return {
                "classification": labels[int(np.argmax(probabilities))],
                "anomaly_score": float(1.0 - probabilities[0]),
                "max_node_risk": float(np.max(node_values)),
                "max_edge_risk": float(np.max(edge_values)),
                "critical_buses": [f"Bus_{i + 1}" for i in np.argsort(node_values)[-5:][::-1]],
                "critical_branches": [self._branch_id(i) for i in np.argsort(edge_values)[-5:][::-1]],
            }

        if self.component == "stgnn":
            nodes = torch.tensor(np.stack(self.node_frames), dtype=torch.float32, device=self.device).unsqueeze(0)
            edges = torch.tensor(np.stack(self.edge_frames), dtype=torch.float32, device=self.device).unsqueeze(0)
            node_risk, edge_risk = self.model(nodes, edges)
            node_values = node_risk.squeeze(0).cpu().numpy()
            edge_values = edge_risk.squeeze(0).cpu().numpy()
            return {
                "forecast_horizon_steps": 5,
                "max_future_node_risk": float(np.max(node_values)),
                "max_future_edge_risk": float(np.max(edge_values)),
                "critical_buses": [f"Bus_{i + 1}" for i in np.argsort(node_values)[-5:][::-1]],
                "critical_branches": [self._branch_id(i) for i in np.argsort(edge_values)[-5:][::-1]],
            }

        sample = torch.tensor(self.temporal_frames[-1], dtype=torch.float32, device=self.device).unsqueeze(0)
        reconstructed, pred_p, pred_q, pred_v, pred_theta = self.model(sample)
        physics_loss, breakdown = self.physics_loss(pred_p, pred_q, pred_v, pred_theta)
        reconstruction_mse = torch.mean((reconstructed - sample) ** 2).item()
        max_voltage_violation = max(
            float(torch.clamp(0.85 - pred_v, min=0.0).max().item()),
            float(torch.clamp(pred_v - 1.15, min=0.0).max().item()),
        )
        balance_loss = float(breakdown["loss_power_balance"])
        return {
            "reconstruction_mse": float(reconstruction_mse),
            "physics_loss": float(physics_loss.item()),
            "physics_consistency_score": float(math.exp(-min(float(physics_loss.item()), 50.0))),
            "physics_violation": bool(max_voltage_violation > 0.0 or balance_loss > 0.05),
            "max_voltage_violation_pu": max_voltage_violation,
            "loss_breakdown": {key: float(value) for key, value in breakdown.items()},
        }

    @staticmethod
    def _branch_id(index: int) -> str:
        return f"L_line_{index}" if index < 35 else f"L_trafo_{index - 35}"


class MQTTModelService:
    def __init__(self, runtime: IEEE39ModelRuntime):
        self.runtime = runtime
        self.client = create_client(f"pypy_{runtime.component}_runtime")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.heartbeat_path = Path(f"/tmp/pypy_{runtime.component}_heartbeat.json")

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            client.subscribe(TELEMETRY_TOPIC)
            LOGGER.info("%s runtime subscribed to %s", self.runtime.component, TELEMETRY_TOPIC)
        else:
            LOGGER.error("MQTT connection failed: %s", reason_code)

    def on_message(self, client, userdata, message):
        try:
            telemetry = json.loads(message.payload.decode("utf-8"))
            result = self.runtime.process(telemetry)
            if result is not None:
                client.publish(OUTPUT_TOPICS[self.runtime.component], json.dumps(result, allow_nan=False))
        except (json.JSONDecodeError, UnicodeDecodeError, TelemetryFeatureError, ValueError, RuntimeError) as exc:
            LOGGER.warning("%s inference skipped: %s", self.runtime.component, exc)
        except Exception:
            LOGGER.exception("Unhandled %s inference failure", self.runtime.component)
        finally:
            self.publish_status(client)

    def publish_status(self, client):
        status = self.runtime.readiness.snapshot(stale_after=15.0)
        encoded = json.dumps(status, allow_nan=False)
        self.heartbeat_path.write_text(encoded, encoding="utf-8")
        client.publish(f"grid/ai/status/{self.runtime.component}", encoded, retain=True)

    def run(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.client.loop_forever()


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(message)s")
    runtime = IEEE39ModelRuntime()
    LOGGER.info("Loaded %s checkpoint %s", runtime.component, runtime.checkpoint)
    MQTTModelService(runtime).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
