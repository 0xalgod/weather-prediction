"""Feature construction helpers for the multi-city event-level dataset."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from weather_quant.normalization.resolution_rules import parse_bucket_bounds


def native_to_fahrenheit(value: float, unit: str) -> float:
    return value if unit == "F" else value * 9 / 5 + 32


def ordered_bucket_thresholds(
    buckets: Sequence[Mapping[str, Any]], unit: str
) -> list[dict[str, Any]]:
    """Parse and order discrete buckets with continuity-corrected Fahrenheit edges."""

    rows = []
    for bucket in buckets:
        bounds = parse_bucket_bounds(str(bucket["label"]), unit)
        lower = bounds["lower_bound"]
        upper = bounds["upper_bound"]
        rows.append(
            {
                **dict(bucket),
                **bounds,
                "lower_threshold_f": (
                    native_to_fahrenheit(float(lower) - 0.5, unit)
                    if lower is not None
                    else None
                ),
                "upper_threshold_f": (
                    native_to_fahrenheit(float(upper) + 0.5, unit)
                    if upper is not None
                    else None
                ),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            float("-inf") if row["lower_bound"] is None else row["lower_bound"]
        ),
    )


def aggregate_gefs_messages(messages: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    """Create locked daily peak/spread features from complete paired steps."""

    values = {
        (int(row["step"]), str(row["product"])): float(row["value_f"])
        for row in messages
    }
    steps = sorted({step for step, product in values if product == "geavg"})
    expected = {
        (step, product) for step in steps for product in ("geavg", "gespr")
    }
    if not steps or set(values) != expected:
        raise ValueError("GEFS messages do not form complete mean/spread step pairs")
    peak_step = max(steps, key=lambda step: (values[(step, "geavg")], -step))
    return {
        "gefs_overlap_mean_max_f": values[(peak_step, "geavg")],
        "gefs_overlap_spread_at_mean_max_f": values[(peak_step, "gespr")],
        "gefs_max_block_spread_f": max(values[(step, "gespr")] for step in steps),
        "gefs_overlap_peak_step": peak_step,
    }
