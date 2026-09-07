from scripts.evaluate_us_nbm_local_day_semantics import (
    evaluate_window,
    station_from_resolution_url,
)


def test_station_from_resolution_url():
    assert (
        station_from_resolution_url(
            "https://www.wunderground.com/history/daily/us/il/chicago/KORD"
        )
        == "KORD"
    )
    assert (
        station_from_resolution_url("https://www.weather.gov/wrh/timeseries?site=katl")
        == "KATL"
    )


def test_eastern_daylight_window_has_sixteen_hour_overlap():
    result = evaluate_window("2026-05-15", "America/New_York", [12, 30])
    assert result["market_start_utc"] == "2026-05-15T04:00:00Z"
    assert result["market_end_utc"] == "2026-05-16T04:00:00Z"
    assert result["overlap_hours"] == 16
    assert result["nbm_hours_outside_market"] == 2
    assert not result["exact_window_equivalence"]


def test_spring_dst_transition_has_twenty_three_hour_market_day():
    result = evaluate_window("2026-03-08", "America/Chicago", [12, 30])
    assert result["market_duration_hours"] == 23
    assert result["utc_offset_at_local_start_hours"] == -6
    assert result["utc_offset_at_local_end_hours"] == -5
