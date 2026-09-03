from datetime import datetime, timezone

from weather_quant.ingestion.polymarket_price_history import (
    parse_utc,
    select_events,
    summarize_coverage,
    validate_history,
    yes_token_rows,
)


def event(event_id="2", end="2026-08-01T12:00:00Z"):
    return {
        "id": event_id,
        "title": "Highest temperature in Chicago on August 1?",
        "creationDate": "2026-07-30T10:00:00.100000Z",
        "endDate": end,
        "closedTime": "2026-08-02T10:00:00.900000Z",
        "closed": True,
        "markets": [
            {
                "id": "m1",
                "groupItemTitle": "80-81°F",
                "umaResolutionStatus": "resolved",
                "outcomes": '["Yes", "No"]',
                "clobTokenIds": '["yes", "no"]',
            }
        ],
    }


def test_parse_utc_accepts_gamma_five_digit_fraction_on_python39():
    parsed = parse_utc("2026-08-23T00:57:43.55602Z")
    assert parsed.microsecond == 556020


def test_selection_and_yes_window_are_deterministic():
    older = event("1", "2026-07-31T12:00:00Z")
    selected = select_events([older, event()], datetime(2026, 9, 3, tzinfo=timezone.utc), 1)
    assert [item["id"] for item in selected] == ["2"]
    rows = yes_token_rows(selected)
    assert rows[0]["yes_token_id"] == "yes"
    assert rows[0]["request_start_ts"] == 1785405601
    assert rows[0]["request_end_ts"] == 1785664800


def test_invalid_market_is_excluded():
    candidate = event()
    candidate["markets"][0]["umaResolutionStatus"] = "proposed"
    assert select_events([candidate], datetime(2026, 9, 3, tzinfo=timezone.utc), 30) == []


def test_history_validation_and_coverage_keep_empty_and_error_denominators():
    valid = validate_history([{"t": 10, "p": 0.2}, {"t": 11, "p": 0.3}], 10, 11)
    assert valid["response_strictly_increasing"] is True
    rows = [
        {"event_id": "1", "request_ok": True, **valid},
        {"event_id": "1", "request_ok": True, **validate_history([], 10, 11)},
        {"event_id": "2", "request_ok": False, "point_count": 0},
    ]
    summary = summarize_coverage(rows)
    assert summary["selected_event_count"] == 2
    assert summary["tokens_with_any_history_rate"] == 1 / 3
    assert summary["request_error_rate"] == 1 / 3
    assert summary["out_of_window_point_rate"] == 0
