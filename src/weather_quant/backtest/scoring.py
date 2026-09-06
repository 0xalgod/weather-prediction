"""Multiclass probability scoring primitives for ordered weather buckets."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


def ordered_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: float("-inf") if row["lower_bound"] is None else row["lower_bound"],
    )


def score_probabilities(
    probabilities: Sequence[float], winner_index: int, probability_floor: float
) -> dict[str, float]:
    """Score one exhaustive categorical distribution and ordered outcome."""

    values = [float(value) for value in probabilities]
    if not values or not 0 <= winner_index < len(values):
        raise ValueError("invalid probability vector or winner index")
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in values):
        raise ValueError("probability outside [0, 1]")
    if abs(math.fsum(values) - 1.0) > 1e-9:
        raise ValueError("probabilities do not sum to one")
    if not 0 < probability_floor < 1:
        raise ValueError("probability floor must be inside (0, 1)")
    one_hot = [1.0 if index == winner_index else 0.0 for index in range(len(values))]
    cumulative_probability = 0.0
    cumulative_outcome = 0.0
    rps_terms = []
    for index in range(len(values) - 1):
        cumulative_probability += values[index]
        cumulative_outcome += one_hot[index]
        rps_terms.append((cumulative_probability - cumulative_outcome) ** 2)
    return {
        "multiclass_log_loss": -math.log(max(values[winner_index], probability_floor)),
        "multiclass_brier_score": math.fsum(
            (probability - outcome) ** 2 for probability, outcome in zip(values, one_hot)
        ),
        "ranked_probability_score": math.fsum(rps_terms) / (len(values) - 1),
        "winning_bucket_probability": values[winner_index],
    }


def mean_metrics(rows: Sequence[Mapping[str, float]]) -> dict[str, float]:
    if not rows:
        raise ValueError("cannot average empty metrics")
    keys = tuple(rows[0])
    return {key: math.fsum(float(row[key]) for row in rows) / len(rows) for key in keys}


def paired_bootstrap_mean_difference(
    left: Sequence[float], right: Sequence[float], repetitions: int, seed: int
) -> dict[str, float]:
    """Bootstrap paired date-level left-minus-right mean differences."""

    if len(left) != len(right) or not left or repetitions < 1:
        raise ValueError("paired bootstrap inputs are invalid")
    differences = [float(a) - float(b) for a, b in zip(left, right)]
    generator = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        samples.append(
            math.fsum(differences[generator.randrange(len(differences))] for _ in differences)
            / len(differences)
        )
    samples.sort()

    def percentile(probability: float) -> float:
        position = probability * (len(samples) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return samples[lower]
        return samples[lower] + (samples[upper] - samples[lower]) * (position - lower)

    return {
        "mean_difference": math.fsum(differences) / len(differences),
        "ci95_lower": percentile(0.025),
        "ci95_upper": percentile(0.975),
    }


def paired_cluster_bootstrap_mean_difference(
    left: Sequence[float],
    right: Sequence[float],
    clusters: Sequence[str],
    repetitions: int,
    seed: int,
) -> dict[str, float]:
    """Bootstrap paired differences by resampling whole dependence clusters."""

    if len(left) != len(right) or len(left) != len(clusters) or not left or repetitions < 1:
        raise ValueError("paired cluster bootstrap inputs are invalid")
    grouped: dict[str, list[float]] = defaultdict(list)
    for left_value, right_value, cluster in zip(left, right, clusters):
        grouped[str(cluster)].append(float(left_value) - float(right_value))
    cluster_ids = sorted(grouped)
    generator = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        selected = [cluster_ids[generator.randrange(len(cluster_ids))] for _ in cluster_ids]
        differences = [value for cluster in selected for value in grouped[cluster]]
        samples.append(math.fsum(differences) / len(differences))
    samples.sort()

    def percentile(probability: float) -> float:
        position = probability * (len(samples) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return samples[lower]
        return samples[lower] + (samples[upper] - samples[lower]) * (position - lower)

    observed = [float(a) - float(b) for a, b in zip(left, right)]
    return {
        "mean_difference": math.fsum(observed) / len(observed),
        "ci95_lower": percentile(0.025),
        "ci95_upper": percentile(0.975),
        "cluster_count": float(len(cluster_ids)),
    }
