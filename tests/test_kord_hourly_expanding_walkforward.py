import pytest

from scripts.run_kord_hourly_expanding_walkforward import evaluate_gates, score_rows


def test_score_rows_reports_expanding_improvement_and_bias():
    rows = [
        {
            "actual_c": 10.0,
            "expanding_ridge_c": 10.5,
            "static_ridge_c": 12.0,
            "persistence_c": 12.0,
            "harmonic_climatology_c": 13.0,
        },
        {
            "actual_c": 20.0,
            "expanding_ridge_c": 19.5,
            "static_ridge_c": 18.0,
            "persistence_c": 18.0,
            "harmonic_climatology_c": 17.0,
        },
    ]

    score = score_rows(rows)

    assert score["events"] == 2
    assert score["expanding_ridge"]["mae_c"] == pytest.approx(0.5)
    assert score["expanding_ridge"]["bias_c"] == pytest.approx(0.0)
    assert score["mae_improvement_vs_persistence"] == pytest.approx(0.75)
    assert score["mae_improvement_vs_static_ridge"] == pytest.approx(0.75)


def test_evaluate_gates_requires_skill_and_bias():
    thresholds = {
        "minimum_mae_improvement_vs_persistence": 0.05,
        "maximum_absolute_bias_c": 1.0,
    }
    passing = {
        "mae_improvement_vs_persistence": 0.06,
        "expanding_ridge": {"bias_c": -0.9},
    }
    failing = {
        "mae_improvement_vs_persistence": 0.04,
        "expanding_ridge": {"bias_c": -1.1},
    }

    assert all(evaluate_gates(passing, thresholds).values())
    assert not any(evaluate_gates(failing, thresholds).values())
