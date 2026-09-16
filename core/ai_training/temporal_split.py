"""Leakage-resistant temporal partitioning for the committed IEEE-39 CSV.

The CSV has one row per scenario_id, so scenario_id cannot group a temporal run.
Rows are stored as contiguous label blocks.  We therefore split each label block
chronologically first and construct windows independently inside each split.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TemporalPartition:
    name: str
    raw_indices: np.ndarray


def chronological_label_partitions(df: pd.DataFrame, ratios=(0.70, 0.15, 0.15)) -> dict[str, TemporalPartition]:
    if not np.isclose(sum(ratios), 1.0):
        raise ValueError("partition ratios must sum to one")
    parts = {"train": [], "validation": [], "test": []}
    for _, group in df.groupby("label", sort=False):
        indices = group.index.to_numpy(dtype=np.int64)
        train_end = int(ratios[0] * len(indices))
        validation_end = train_end + int(ratios[1] * len(indices))
        parts["train"].extend(indices[:train_end])
        parts["validation"].extend(indices[train_end:validation_end])
        parts["test"].extend(indices[validation_end:])
    return {
        name: TemporalPartition(name, np.asarray(indices, dtype=np.int64))
        for name, indices in parts.items()
    }


def contiguous_runs(indices: np.ndarray) -> list[np.ndarray]:
    if len(indices) == 0:
        return []
    ordered = np.sort(indices)
    boundaries = np.where(np.diff(ordered) != 1)[0] + 1
    return [run for run in np.split(ordered, boundaries) if len(run)]


def window_spans(indices: np.ndarray, sequence_length: int, future_horizon: int = 0) -> list[np.ndarray]:
    width = sequence_length + future_horizon
    spans = []
    for run in contiguous_runs(indices):
        for start in range(0, len(run) - width + 1):
            spans.append(run[start:start + width])
    return spans


def overlap_report(spans_by_partition: dict[str, list[np.ndarray]]) -> dict:
    raw = {
        name: set(int(v) for span in spans for v in span)
        for name, spans in spans_by_partition.items()
    }
    pairs = {}
    names = ("train", "validation", "test")
    for left, right in ((names[0], names[1]), (names[0], names[2]), (names[1], names[2])):
        shared = raw[left] & raw[right]
        affected_left = sum(bool(set(map(int, span)) & shared) for span in spans_by_partition[left])
        affected_right = sum(bool(set(map(int, span)) & shared) for span in spans_by_partition[right])
        pairs[f"{left}_{right}"] = {
            "overlapping_raw_observations": len(shared),
            "left_sequences_affected": affected_left,
            "right_sequences_affected": affected_right,
            "left_percentage": 100.0 * affected_left / max(1, len(spans_by_partition[left])),
            "right_percentage": 100.0 * affected_right / max(1, len(spans_by_partition[right])),
        }
    return {
        "raw_observations_by_partition": {name: len(values) for name, values in raw.items()},
        "sequences_by_partition": {name: len(spans) for name, spans in spans_by_partition.items()},
        "pairwise_overlap": pairs,
    }
