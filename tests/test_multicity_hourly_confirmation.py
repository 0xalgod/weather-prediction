import pytest

from scripts.run_multicity_hourly_confirmation import (
    confirmation_checks,
    date_cluster_bootstrap,
    score_predictions,
)


def prediction(station, target_date, actual, model, persistence):
    return {
        "station": station,
        "target_date": target_date,
        "actual_c": actual,
        "expanding_ridge_c": model,
        "persistence_c": persistence,
        "harmonic_climatology_c": persistence + 1,
    }


def test_date_cluster_bootstrap_is_paired_and_deterministic():
    rows = [
        prediction("A", "2026-01-01", 10, 10.5, 12),
        prediction("B", "2026-01-01", 20, 20.5, 22),
        prediction("A", "2026-01-02", 11, 11.5, 13),
        prediction("B", "2026-01-02", 21, 21.5, 23),
    ]

    first = date_cluster_bootstrap(rows, 100, 7)
    second = date_cluster_bootstrap(rows, 100, 7)

    assert first == second
    assert first["cluster_count"] == 2
    assert first["mean_paired_mae_reduction_c"] == pytest.approx(1.5)
    assert first["lower_95pct_c"] == pytest.approx(1.5)


def test_confirmation_checks_combine_pooled_ci_and_station_gates():
    rows = [
        prediction("A", "2026-01-01", 10, 10.5, 12),
        prediction("B", "2026-01-01", 20, 20.5, 22),
        prediction("C", "2026-01-01", 30, 30.5, 32),
        prediction("D", "2026-01-01", 40, 40.5, 42),
        prediction("E", "2026-01-01", 50, 50.5, 52),
    ]
    pooled = score_predictions(rows)
    stations = {
        station: score_predictions([row])
        for station, row in zip(("A", "B", "C", "D", "E"), rows)
    }
    bootstrap = {"lower_95pct_c": 0.5}
    gates = {
        "minimum_pooled_mae_improvement_vs_persistence": 0.05,
        "maximum_pooled_absolute_bias_c": 1.0,
        "minimum_date_cluster_bootstrap_95pct_lower_bound_mae_reduction_c": 0.0,
        "minimum_stations_with_positive_mae_improvement": 4,
        "minimum_stations_meeting_5pct_skill_and_1c_bias": 3,
    }

    assert all(confirmation_checks(pooled, stations, bootstrap, gates).values())
