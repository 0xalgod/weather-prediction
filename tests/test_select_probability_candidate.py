import numpy as np
import pytest

from scripts.select_probability_candidate import (
    c_to_f,
    candidate_variants,
    score_samples,
)


def test_celsius_to_fahrenheit():
    assert c_to_f(0) == pytest.approx(32)
    assert c_to_f(10) == pytest.approx(50)


def test_empirical_crps_is_zero_for_perfect_degenerate_forecast():
    rows = [{"station": "X", "target_date": "2026-01-01", "point_f": 70, "actual_f": 70}]
    samples = np.zeros((1, 101))

    aggregate, details = score_samples(rows, samples, 1e-6)

    assert aggregate["mean_crps_f"] == pytest.approx(0)
    assert aggregate["coverage80"] == pytest.approx(1)
    assert details[0]["crps_f"] == pytest.approx(0)


def test_crps_reduction_is_finite_for_full_deterministic_sample_grid():
    rows = [
        {"station": "X", "target_date": "2026-01-01", "point_f": 100, "actual_f": 105}
    ]
    samples = np.linspace(-25, 25, 2001)[None, :]

    with np.errstate(over="raise", invalid="raise", divide="raise"):
        aggregate, _ = score_samples(rows, samples, 1e-6)

    assert np.isfinite(aggregate["mean_crps_f"])


def test_candidate_grid_is_fully_expanded():
    config = {
        "candidates": {
            "student_t_residual": {"degrees_of_freedom": [3, 5]},
            "empirical_residual": {"gaussian_jitter_bandwidth_f": [0.5, 1.0]},
            "quantile_gbt_residual": {"parameter_grid": [{"max_depth": 2}]},
        }
    }

    variants = candidate_variants(config)

    assert [row["family"] for row in variants] == [
        "gaussian_residual",
        "student_t_residual",
        "student_t_residual",
        "empirical_residual",
        "empirical_residual",
        "quantile_gbt_residual",
    ]
