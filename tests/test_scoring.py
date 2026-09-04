import math

from weather_quant.backtest.scoring import (
    paired_bootstrap_mean_difference,
    score_probabilities,
)


def test_perfect_and_uniform_multiclass_scores():
    perfect = score_probabilities([0.0, 1.0, 0.0], 1, 1e-12)
    assert perfect == {
        "multiclass_log_loss": 0.0,
        "multiclass_brier_score": 0.0,
        "ranked_probability_score": 0.0,
        "winning_bucket_probability": 1.0,
    }
    uniform = score_probabilities([1 / 3] * 3, 1, 1e-12)
    assert math.isclose(uniform["multiclass_log_loss"], math.log(3))
    assert math.isclose(uniform["multiclass_brier_score"], 2 / 3)
    assert math.isclose(uniform["ranked_probability_score"], 1 / 9)


def test_paired_bootstrap_is_deterministic():
    first = paired_bootstrap_mean_difference([2, 3], [1, 1], 100, 7)
    second = paired_bootstrap_mean_difference([2, 3], [1, 1], 100, 7)
    assert first == second
    assert first["mean_difference"] == 1.5
