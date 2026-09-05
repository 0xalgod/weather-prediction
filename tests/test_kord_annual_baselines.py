from datetime import date

from scripts.score_kord_annual_baselines import (
    circular_day_distance,
    integer_celsius_buckets,
)


def test_integer_celsius_buckets_are_exhaustive_with_fahrenheit_boundaries() -> None:
    buckets = integer_celsius_buckets(-1, 1)
    assert buckets[0]["lower_bound"] is None
    assert buckets[0]["upper_bound"] == 31.1
    assert buckets[1]["lower_bound"] == 31.1
    assert buckets[-1]["upper_bound"] is None


def test_circular_day_distance_wraps_year_boundary() -> None:
    left = date(2025, 12, 31).timetuple().tm_yday
    right = date(2026, 1, 1).timetuple().tm_yday
    assert circular_day_distance(left, right) == 1
