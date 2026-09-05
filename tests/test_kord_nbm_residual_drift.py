import pytest

from scripts.diagnose_kord_nbm_residual_drift import metrics, population_std


def test_population_std_uses_population_denominator() -> None:
    assert population_std([1.0, 3.0]) == 1.0


def test_residual_metrics_and_coverage() -> None:
    rows = [
        {"daily_maximum_dry_bulb_f": 12.0, "nbm_mean_f": 10.0, "nbm_standard_deviation_f": 2.0},
        {"daily_maximum_dry_bulb_f": 8.0, "nbm_mean_f": 10.0, "nbm_standard_deviation_f": 2.0},
    ]
    result = metrics(rows, {"80": 1.2815515655446004})
    assert result["mean_residual_f"] == 0
    assert result["rmse_f"] == 2
    assert result["standardized_residual_standard_deviation"] == 1
    assert result["central_80_coverage"] == pytest.approx(1.0)
