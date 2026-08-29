"""Minimal reproducibility pipeline used by the repository smoke test.

This module intentionally contains no trading logic. It proves that versioned
configuration, deterministic transformations, and evaluation can run through
the package's ``src`` layout before real data sources are introduced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


def load_config(path: Path) -> Mapping[str, object]:
    """Load a versioned JSON configuration file using the standard library."""

    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def celsius_to_fahrenheit(value: float) -> float:
    """Convert an exact Celsius value to Fahrenheit without rounding."""

    return (value * 9.0 / 5.0) + 32.0


def ensemble_mean(values: Iterable[float]) -> float:
    """Calculate an ensemble mean and reject an empty ensemble."""

    members = tuple(float(value) for value in values)
    if not members:
        raise ValueError("ensemble must contain at least one member")
    return sum(members) / len(members)


def brier_score(probability: float, outcome: int) -> float:
    """Return the binary Brier score for a probability and observed outcome."""

    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    if outcome not in (0, 1):
        raise ValueError("outcome must be 0 or 1")
    return (probability - outcome) ** 2


def run_smoke_pipeline(config_path: Path) -> Mapping[str, object]:
    """Run a deterministic config → normalize → feature → evaluate flow."""

    config = load_config(config_path)
    ensemble_celsius = (20.0, 21.0, 22.0)
    mean_celsius = ensemble_mean(ensemble_celsius)
    probability = 2.0 / 3.0

    return {
        "project_name": config["project"]["name"],  # type: ignore[index]
        "live_trading_enabled": config["project"]["live_trading_enabled"],  # type: ignore[index]
        "ensemble_mean_celsius": mean_celsius,
        "ensemble_mean_fahrenheit": celsius_to_fahrenheit(mean_celsius),
        "brier_score": brier_score(probability, 1),
    }
