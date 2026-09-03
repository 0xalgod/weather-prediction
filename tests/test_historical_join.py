from weather_quant.features.historical_join import (
    event_join_identity,
    exact_target_record,
    target_date_from_event,
)


def sample_event():
    return {
        "id": "10",
        "title": "Highest temperature in Chicago on August 28?",
        "endDate": "2026-08-28T12:00:00Z",
        "markets": [
            {
                "id": "1",
                "conditionId": "c1",
                "groupItemTitle": "79°F or below",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0","1"]',
                "clobTokenIds": '["y1","n1"]',
            },
            {
                "id": "2",
                "conditionId": "c2",
                "groupItemTitle": "80-81°F",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["1","0"]',
                "clobTokenIds": '["y2","n2"]',
            },
            {
                "id": "3",
                "conditionId": "c3",
                "groupItemTitle": "82°F or higher",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0","1"]',
                "clobTokenIds": '["y3","n3"]',
            },
        ],
    }


def test_event_identity_locks_dates_partition_and_winner():
    event = sample_event()
    assert target_date_from_event(event).isoformat() == "2026-08-28"
    joined = event_join_identity(event)
    assert joined["decision_time_utc"] == "2026-08-27T11:00:00Z"
    assert joined["target_valid_time_utc"] == "2026-08-29T00:00:00Z"
    assert joined["forecast_run_date"] == "20260827"
    assert joined["winning_bucket_label"] == "80-81°F"


def test_exact_target_record_rejects_missing_distribution():
    complete = {
        "valid_time_utc": "2026-08-29T00:00:00Z",
        "mean_f": 80,
        "standard_deviation_f": 3,
        "p10_f": 76,
        "p25_f": 78,
        "p50_f": 80,
        "p75_f": 82,
        "p90_f": 84,
    }
    assert exact_target_record([complete], complete["valid_time_utc"])["mean_f"] == 80
