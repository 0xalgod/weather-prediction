"""Cohort and geographic sampling helpers for multi-city GEFS features."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def longitude_stratified_sample(
    rows: Sequence[Mapping[str, Any]], sample_size: int
) -> list[dict[str, Any]]:
    """Select evenly spaced order statistics without inspecting forecast values."""

    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            float(row["longitude"]),
            float(row["latitude"]),
            str(row["target_date"]),
            str(row["event_id"]),
        ),
    )
    if sample_size < 2 or len(ordered) < sample_size:
        raise ValueError("sample requires at least two rows and cannot exceed population")
    indices = [
        round(index * (len(ordered) - 1) / (sample_size - 1))
        for index in range(sample_size)
    ]
    if len(set(indices)) != sample_size:
        raise ValueError("order-statistic selection produced duplicate indices")
    return [ordered[index] for index in indices]
