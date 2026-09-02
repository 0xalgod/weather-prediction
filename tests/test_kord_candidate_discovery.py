from datetime import datetime, timezone

from weather_quant.ingestion.kord_candidate import audit_upcoming_kord_candidate


def event() -> dict:
    return {
        "id": "10",
        "title": "Highest temperature in Chicago on September 5?",
        "endDate": "2026-09-05T12:00:00Z",
        "active": True,
        "closed": False,
        "resolutionSource": "https://www.wunderground.com/history/daily/us/il/chicago/KORD",
        "description": (
            "Chicago O'Hare Intl Airport Station KORD. This market can not resolve until "
            "the first data point for the following date has been published."
        ),
        "markets": [
            {
                "id": "20",
                "conditionId": "0xabc",
                "clobTokenIds": '["yes-token", "no-token"]',
            }
        ],
    }


def test_exact_future_wunderground_kord_event_qualifies() -> None:
    result = audit_upcoming_kord_candidate(
        event(), datetime(2026, 9, 2, tzinfo=timezone.utc)
    )
    assert result["qualified"] is True
    assert result["token_identities"][0]["token_ids"] == ["yes-token", "no-token"]


def test_noaa_primary_with_wunderground_fallback_does_not_qualify() -> None:
    candidate = event()
    candidate["resolutionSource"] = "https://www.weather.gov/wrh/timeseries?site=kord"
    candidate["description"] += " Wunderground may be used as a fallback."
    result = audit_upcoming_kord_candidate(
        candidate, datetime(2026, 9, 2, tzinfo=timezone.utc)
    )
    assert result["checks"]["primary_resolution_source_wunderground_kord"] is False
    assert result["qualified"] is False


def test_past_or_incomplete_event_fails_closed() -> None:
    candidate = event()
    candidate["endDate"] = "2026-09-01T12:00:00Z"
    candidate["markets"][0]["conditionId"] = ""
    result = audit_upcoming_kord_candidate(
        candidate, datetime(2026, 9, 2, tzinfo=timezone.utc)
    )
    assert result["checks"]["observed_future"] is False
    assert result["checks"]["nested_market_identities_complete"] is False
    assert result["qualified"] is False
