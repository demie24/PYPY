"""Canonical IEEE-39 telemetry-to-model feature conversion.

The stored LSTM was trained on the flattened order P, Q, V, theta (39 values
each).  GNN and ST-GNN models use per-bus P/Q in per-unit plus V/theta, and
five per-branch features.  Keeping these conversions here prevents runtime
services from silently using incompatible feature orders or units.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np


BUS_COUNT = 39
BRANCH_COUNT = 46
TEMPORAL_FEATURE_COUNT = BUS_COUNT * 4
NODE_FEATURE_COUNT = 4
EDGE_FEATURE_COUNT = 5


class TelemetryFeatureError(ValueError):
    """Raised when telemetry is unsafe or incompatible with model inference."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class IEEE39FeatureFrame:
    timestamp: float
    temporal: np.ndarray
    nodes: np.ndarray
    edges: np.ndarray
    branch_ids: tuple[str, ...]
    solver_status: Mapping[str, Any]
    telemetry_id: str | None = None
    experiment_id: str | None = None
    scenario_id: str | None = None
    correlation_id: str | None = None


def _finite_float(value: Any, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise TelemetryFeatureError("invalid_numeric_value", field) from exc
    if not np.isfinite(parsed):
        raise TelemetryFeatureError("non_finite_telemetry", field)
    return parsed


def _ordered_branch_ids(lines: Mapping[str, Any], branch_ids: Sequence[str] | None) -> tuple[str, ...]:
    if branch_ids is not None:
        ordered = tuple(branch_ids)
    else:
        # Digital Twin inserts pandapower lines first, then transformers.  A
        # numeric sort preserves that canonical model-training order.
        def key(branch_id: str) -> tuple[int, int]:
            prefix = 0 if branch_id.startswith("L_line_") else 1
            try:
                index = int(branch_id.rsplit("_", 1)[-1])
            except ValueError as exc:
                raise TelemetryFeatureError("invalid_branch_id", branch_id) from exc
            return prefix, index

        ordered = tuple(sorted(lines, key=key))
    if len(ordered) != BRANCH_COUNT or set(ordered) != set(lines):
        raise TelemetryFeatureError(
            "invalid_branch_count",
            f"expected {BRANCH_COUNT}, received {len(lines)}",
        )
    return ordered


def extract_ieee39_features(
    telemetry: Mapping[str, Any],
    *,
    branch_ids: Sequence[str] | None = None,
) -> IEEE39FeatureFrame:
    """Validate one IEEE-39 frame and return inputs for all active AI models."""
    if telemetry.get("grid_name") != "ieee39":
        raise TelemetryFeatureError("unsupported_grid", str(telemetry.get("grid_name")))

    solver_status = telemetry.get("solver_status") or {}
    if solver_status and not solver_status.get("converged", False):
        raise TelemetryFeatureError(
            "power_flow_non_convergence",
            str(solver_status.get("mode", "failed")),
        )

    try:
        state = telemetry["state"]
        buses = state["buses"]
        lines = state["lines"]
        breakers = state["breakers"]
    except (KeyError, TypeError) as exc:
        raise TelemetryFeatureError("missing_state", str(exc)) from exc

    if len(buses) != BUS_COUNT:
        raise TelemetryFeatureError("invalid_bus_count", f"expected {BUS_COUNT}, received {len(buses)}")

    p_mw, q_mvar, voltage, angle = [], [], [], []
    node_rows = []
    for index in range(1, BUS_COUNT + 1):
        bus_id = f"Bus_{index}"
        if bus_id not in buses:
            raise TelemetryFeatureError("missing_bus", bus_id)
        bus = buses[bus_id]
        p = _finite_float(bus.get("P_mw"), f"{bus_id}.P_mw")
        q = _finite_float(bus.get("Q_mvar"), f"{bus_id}.Q_mvar")
        v = _finite_float(bus.get("voltage_pu"), f"{bus_id}.voltage_pu")
        theta = _finite_float(bus.get("angle_rad"), f"{bus_id}.angle_rad")
        p_mw.append(p)
        q_mvar.append(q)
        voltage.append(v)
        angle.append(theta)
        node_rows.append((p / 100.0, q / 100.0, v, theta))

    ordered_branches = _ordered_branch_ids(lines, branch_ids)
    edge_rows = []
    for branch_id in ordered_branches:
        line = lines[branch_id]
        p = _finite_float(line.get("P_mw"), f"{branch_id}.P_mw") / 100.0
        q = _finite_float(line.get("Q_mvar"), f"{branch_id}.Q_mvar") / 100.0
        loading = _finite_float(line.get("capacity_pct"), f"{branch_id}.capacity_pct") / 100.0
        closed = 1.0 if breakers.get(branch_id) == "CLOSED" else 0.0
        is_transformer = 1.0 if branch_id.startswith("L_trafo_") else 0.0
        edge_rows.append((p, q, loading, closed * (1.0 - is_transformer), closed * is_transformer))

    temporal = np.asarray(p_mw + q_mvar + voltage + angle, dtype=np.float32)
    nodes = np.asarray(node_rows, dtype=np.float32)
    edges = np.asarray(edge_rows, dtype=np.float32)
    if temporal.shape != (TEMPORAL_FEATURE_COUNT,) or nodes.shape != (BUS_COUNT, NODE_FEATURE_COUNT) or edges.shape != (BRANCH_COUNT, EDGE_FEATURE_COUNT):
        raise TelemetryFeatureError("invalid_feature_shape", f"{temporal.shape}/{nodes.shape}/{edges.shape}")

    return IEEE39FeatureFrame(
        timestamp=_finite_float(telemetry.get("timestamp"), "timestamp"),
        temporal=temporal,
        nodes=nodes,
        edges=edges,
        branch_ids=ordered_branches,
        solver_status=solver_status,
        telemetry_id=telemetry.get("telemetry_id"),
        experiment_id=telemetry.get("experiment_id"),
        scenario_id=telemetry.get("scenario_id"),
        correlation_id=telemetry.get("correlation_id"),
    )
