import numpy as np

from scripts.run_protected_probability_test import (
    date_cluster_bootstrap,
    gate_checks,
    pit_diagnostic,
)


def test_pit_diagnostic_is_uniform_for_even_ranks():
    sample = np.linspace(-5, 5, 1001)
    rows = [
        {"point_f": 0.0, "actual_f": float(value)}
        for value in np.linspace(-4.5, 4.5, 10)
    ]

    diagnostic = pit_diagnostic(rows, sample)

    assert diagnostic["ten_bin_counts"] == [1] * 10
    assert diagnostic["ece_total_variation_from_uniform"] < 1e-12


def test_date_cluster_bootstrap_preserves_date_clusters():
    candidate = [
        {"station": "A", "target_date": "2026-01-01", "crps_f": 1.0},
        {"station": "B", "target_date": "2026-01-01", "crps_f": 1.0},
        {"station": "A", "target_date": "2026-01-02", "crps_f": 1.0},
    ]
    baseline = [
        {"station": "A", "target_date": "2026-01-01", "crps_f": 2.0},
        {"station": "B", "target_date": "2026-01-01", "crps_f": 2.0},
        {"station": "A", "target_date": "2026-01-02", "crps_f": 2.0},
    ]

    result = date_cluster_bootstrap(candidate, baseline, 100, 42)

    assert result["cluster_count"] == 2
    assert result["mean_crps_reduction_f"] == 1.0
    assert result["lower_95pct_f"] == 1.0


def test_gate_checks_require_all_probability_conditions():
    candidate = {
        "mean_crps_f": 1.0,
        "categorical_log_loss": 1.0,
        "coverage80": 0.8,
        "coverage90": 0.9,
    }
    persistence = {"mean_crps_f": 1.2, "categorical_log_loss": 1.2}
    harmonic = {"mean_crps_f": 1.3, "categorical_log_loss": 1.3}
    bootstrap = {"lower_95pct_f": 0.1}
    station_scores = {
        station: {
            "candidate": {"mean_crps_f": 1.0},
            "persistence_gaussian": {"mean_crps_f": 1.2},
            "harmonic_empirical": {"mean_crps_f": 1.3},
        }
        for station in ("A", "B", "C")
    }
    gates = {
        "minimum_pooled_crps_improvement_vs_best_baseline": 0.05,
        "minimum_pooled_log_loss_improvement_vs_best_baseline": 0.02,
        "minimum_target_date_cluster_bootstrap_95pct_lower_bound_crps_reduction_f": 0.0,
        "minimum_80pct_interval_coverage": 0.75,
        "maximum_80pct_interval_coverage": 0.85,
        "minimum_90pct_interval_coverage": 0.86,
        "maximum_90pct_interval_coverage": 0.94,
        "minimum_protected_stations_with_positive_crps_improvement": 2,
    }

    _, checks = gate_checks(
        candidate, persistence, harmonic, bootstrap, station_scores, gates
    )

    assert all(checks.values())
