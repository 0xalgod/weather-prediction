from weather_quant.ingestion.multicity_price_horizon import (
    event_horizon_coverage,
    latest_point_at_or_before,
    stratified_two_per_city,
    summarize_horizons,
)


def test_stratified_sample_uses_temporal_halves() -> None:
    rows = [
        {"city": "A", "target_date": f"2026-01-{day:02d}", "event_id": str(day)}
        for day in range(1, 7)
    ]
    selected = stratified_two_per_city(rows, {"A"})
    assert [row["event_id"] for row in selected] == ["2", "5"]


def test_latest_point_forbids_future() -> None:
    history = [{"t": 90, "p": 0.2}, {"t": 100, "p": 0.3}, {"t": 110, "p": 0.9}]
    assert latest_point_at_or_before(history, 100) == (100, 0.3)


def test_event_horizon_requires_all_fresh_buckets() -> None:
    event = {
        "event_id": "1",
        "city": "A",
        "target_date": "2026-01-02",
        "end_date_utc": "2026-01-02T12:00:00Z",
        "buckets": [
            {"market_id": "m1", "yes_token_id": "t1"},
            {"market_id": "m2", "yes_token_id": "t2"},
        ],
    }
    cutoff = 1767333600  # 2026-01-02 06:00:00Z
    histories = {
        "t1": [{"t": cutoff - 100, "p": 0.4}],
        "t2": [{"t": cutoff - 50000, "p": 0.6}],
    }
    row = event_horizon_coverage(event, histories, [6], 43200)[0]
    assert row["complete_vector"] is True
    assert row["usable_full_vector"] is False
    assert row["raw_probability_sum"] == 1.0


def test_summarize_horizons() -> None:
    rows = [
        {
            "event_id": "1",
            "city": "A",
            "horizon_hours": 6,
            "complete_vector": True,
            "usable_full_vector": True,
        },
        {
            "event_id": "2",
            "city": "B",
            "horizon_hours": 6,
            "complete_vector": False,
            "usable_full_vector": False,
        },
    ]
    summary = summarize_horizons(rows)
    assert summary["by_horizon"]["6"]["usable_full_vector_event_rate"] == 0.5
    assert summary["cities_with_usable_vector_at_any_horizon_count"] == 1
