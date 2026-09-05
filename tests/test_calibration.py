import math

from weather_quant.forecasting.calibration import (
    gaussian_probabilities,
    quantile_probabilities,
    shift_grid,
)


def buckets():
    return [
        {
            "market_id": "1",
            "condition_id": "c1",
            "yes_token_id": "y1",
            "no_token_id": "n1",
            "label": "79°F or below",
            "lower_bound": None,
            "upper_bound": 79,
            "lower_inclusive": True,
            "upper_inclusive": True,
        },
        {
            "market_id": "2",
            "condition_id": "c2",
            "yes_token_id": "y2",
            "no_token_id": "n2",
            "label": "80-81°F",
            "lower_bound": 80,
            "upper_bound": 81,
            "lower_inclusive": True,
            "upper_inclusive": True,
        },
        {
            "market_id": "3",
            "condition_id": "c3",
            "yes_token_id": "y3",
            "no_token_id": "n3",
            "label": "82°F or higher",
            "lower_bound": 82,
            "upper_bound": None,
            "lower_inclusive": True,
            "upper_inclusive": True,
        },
    ]


def test_locked_shift_grid_is_exact():
    values = shift_grid(-5, 5, 0.5)
    assert len(values) == 21
    assert values[0] == -5
    assert values[-1] == 5


def test_probability_transforms_remain_exhaustive():
    forecast = {
        "mean_f": 80,
        "standard_deviation_f": 3,
        "p10_f": 76,
        "p25_f": 78,
        "p50_f": 80,
        "p75_f": 82,
        "p90_f": 84,
    }
    gaussian = gaussian_probabilities(buckets(), forecast, 1.0, 0.75)
    quantile = quantile_probabilities(buckets(), forecast, 1.0, 0.75)
    assert math.isclose(sum(gaussian), 1.0)
    assert math.isclose(sum(quantile), 1.0)
    assert gaussian != quantile
