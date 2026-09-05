"""Interpretable shift/spread calibration for temperature bucket distributions."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from weather_quant.backtest.scoring import mean_metrics, ordered_rows, score_probabilities
from weather_quant.market_model.vertical_slice import (
    gaussian_bucket_probabilities,
    quantile_bucket_probabilities,
)

ProbabilityFunction = Callable[
    [Sequence[Mapping[str, Any]], Mapping[str, Any], float, float], list[float]
]


def gaussian_probabilities(
    buckets: Sequence[Mapping[str, Any]],
    forecast: Mapping[str, Any],
    shift_f: float,
    spread_scale: float,
) -> list[float]:
    if spread_scale <= 0:
        raise ValueError("spread scale must be positive")
    return [
        row["model_probability"]
        for row in gaussian_bucket_probabilities(
            buckets,
            float(forecast["mean_f"]) + shift_f,
            float(forecast["standard_deviation_f"]) * spread_scale,
        )
    ]


def quantile_probabilities(
    buckets: Sequence[Mapping[str, Any]],
    forecast: Mapping[str, Any],
    shift_f: float,
    spread_scale: float,
) -> list[float]:
    """Shift the median and scale every quantile deviation from it."""

    if spread_scale <= 0:
        raise ValueError("spread scale must be positive")
    median = float(forecast["p50_f"])
    transformed = {
        key: median + shift_f + spread_scale * (float(forecast[key]) - median)
        for key in ("p10_f", "p25_f", "p50_f", "p75_f", "p90_f")
    }
    return [row["model_probability"] for row in quantile_bucket_probabilities(buckets, transformed)]


def event_model_score(
    event: Mapping[str, Any],
    probability_function: ProbabilityFunction,
    shift_f: float,
    spread_scale: float,
    probability_floor: float,
) -> dict[str, Any]:
    buckets = ordered_rows(event["buckets"])
    winner_index = next(
        index
        for index, bucket in enumerate(buckets)
        if bucket["market_id"] == event["winning_market_id"]
    )
    probabilities = probability_function(buckets, event["forecast"], shift_f, spread_scale)
    return {
        "probabilities": probabilities,
        "metrics": score_probabilities(probabilities, winner_index, probability_floor),
    }


def shift_grid(minimum: float, maximum: float, step: float) -> list[float]:
    if step <= 0 or maximum < minimum:
        raise ValueError("invalid shift grid")
    count = round((maximum - minimum) / step)
    values = [minimum + index * step for index in range(count + 1)]
    if not math.isclose(values[-1], maximum, abs_tol=1e-12):
        raise ValueError("shift grid bounds are not divisible by step")
    return values


def select_parameters(
    train_events: Sequence[Mapping[str, Any]],
    probability_function: ProbabilityFunction,
    shifts: Sequence[float],
    scales: Sequence[float],
    probability_floor: float,
) -> dict[str, float]:
    """Select locked-grid parameters by train log loss and deterministic tie-break."""

    if not train_events or not shifts or not scales:
        raise ValueError("calibration grid and training events are required")
    candidates = []
    for shift in shifts:
        for scale in scales:
            scores = [
                event_model_score(event, probability_function, shift, scale, probability_floor)[
                    "metrics"
                ]["multiclass_log_loss"]
                for event in train_events
            ]
            candidates.append(
                {
                    "shift_f": float(shift),
                    "spread_scale": float(scale),
                    "train_mean_multiclass_log_loss": math.fsum(scores) / len(scores),
                }
            )
    return min(
        candidates,
        key=lambda row: (
            row["train_mean_multiclass_log_loss"],
            abs(row["shift_f"]),
            abs(row["spread_scale"] - 1.0),
            row["shift_f"],
            row["spread_scale"],
        ),
    )


def aggregate_event_scores(scores: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    return mean_metrics([row["metrics"] for row in scores])
