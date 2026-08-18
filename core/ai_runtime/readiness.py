"""Uniform readiness and heartbeat state for model-serving processes."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelReadiness:
    component: str
    model_loaded: bool = False
    checkpoint: str | None = None
    started_at: float = field(default_factory=time.time)
    last_telemetry_at: float | None = None
    last_inference_at: float | None = None
    last_error: str | None = None
    inference_count: int = 0

    def record_telemetry(self, timestamp: float | None = None) -> None:
        self.last_telemetry_at = time.time() if timestamp is None else timestamp

    def record_inference(self, timestamp: float | None = None) -> None:
        self.last_inference_at = time.time() if timestamp is None else timestamp
        self.last_error = None
        self.inference_count += 1

    def record_error(self, error: Exception | str) -> None:
        self.last_error = str(error)

    def snapshot(self, *, now: float | None = None, stale_after: float = 10.0) -> dict[str, Any]:
        current = time.time() if now is None else now
        telemetry_age = None if self.last_telemetry_at is None else max(0.0, current - self.last_telemetry_at)
        inference_age = None if self.last_inference_at is None else max(0.0, current - self.last_inference_at)
        ready = bool(
            self.model_loaded
            and telemetry_age is not None
            and inference_age is not None
            and telemetry_age <= stale_after
            and inference_age <= stale_after
            and self.last_error is None
        )
        return {
            "component": self.component,
            "ready": ready,
            "model_loaded": self.model_loaded,
            "checkpoint": self.checkpoint,
            "telemetry_age_seconds": telemetry_age,
            "inference_age_seconds": inference_age,
            "inference_count": self.inference_count,
            "last_error": self.last_error,
            "timestamp": int(current * 1000),
        }
