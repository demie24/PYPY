"""Bounded in-process latency and safety counters; not network telemetry."""

from __future__ import annotations
from collections import Counter, defaultdict
from contextlib import contextmanager
import statistics
import time


class MethodologyMetrics:
    def __init__(self):
        self.latencies_ms = defaultdict(list)
        self.safety = Counter()

    @contextmanager
    def timer(self, stage):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.latencies_ms[stage].append((time.perf_counter() - started) * 1000.0)

    def count(self, outcome, amount=1):
        self.safety[outcome] += amount

    def snapshot(self):
        return {
            "latency_scope": "same-process application elapsed time; not network-level MQTT latency",
            "latencies_ms": {stage: {"count": len(values), "mean": statistics.fmean(values),
                "min": min(values), "max": max(values)} for stage, values in self.latencies_ms.items()},
            "safety_counts": dict(self.safety),
        }
