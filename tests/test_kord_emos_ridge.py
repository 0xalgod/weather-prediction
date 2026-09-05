import pytest

from scripts.run_kord_emos_ridge import feature_vector, fit_ridge, predict


def row(nbm_mean: float, label: float) -> dict:
    return {
        "nbm_mean_f": nbm_mean,
        "gefs_overlap_mean_max_f": nbm_mean,
        "day_of_year_sin": 0.0,
        "day_of_year_cos": 1.0,
        "nbm_version": "4.3",
        "gefs_exact_partition": True,
        "gefs_outside_local_seconds": 0.0,
        "daily_maximum_dry_bulb_f": label,
    }


def test_feature_vector_has_locked_order_and_length() -> None:
    assert feature_vector(row(10.0, 12.0)) == [10.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0]


def test_ridge_prediction_learns_simple_temperature_relation() -> None:
    rows = [row(float(value), float(value + 2)) for value in range(20)]
    model = fit_ridge(rows, 0.1)
    assert predict(model, row(10.0, 0.0)) == pytest.approx(12.0, abs=0.02)
