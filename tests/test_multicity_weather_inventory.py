from scripts.build_multicity_weather_inventory import (
    city_from_title,
    normalize_event,
    temperature_unit,
)


def event() -> dict:
    return {
        "id": "1",
        "title": "Highest temperature in Chicago on September 7?",
        "eventDate": "2026-09-07",
        "closed": True,
        "resolutionSource": "https://example.com/KORD",
        "description": "Highest reading in degrees Fahrenheit.",
        "markets": [
            {
                "id": "10",
                "conditionId": "c1",
                "clobTokenIds": '["yes1", "no1"]',
                "outcomePrices": '["1", "0"]',
                "umaResolutionStatus": "resolved",
                "groupItemTitle": "80°F or below",
            },
            {
                "id": "11",
                "conditionId": "c2",
                "clobTokenIds": '["yes2", "no2"]',
                "outcomePrices": '["0", "1"]',
                "umaResolutionStatus": "resolved",
                "groupItemTitle": "81°F or higher",
            },
        ],
    }


def test_city_and_unit_parsing() -> None:
    assert city_from_title(event()["title"]) == "Chicago"
    assert temperature_unit(event()["description"]) == "F"


def test_normalize_event_retains_one_terminal_winner() -> None:
    row, reasons = normalize_event(event(), "abc")
    assert reasons == []
    assert row["winner_market_id"] == "10"
    assert row["bucket_count"] == 2


def test_multiple_winners_are_excluded() -> None:
    candidate = event()
    candidate["markets"][1]["outcomePrices"] = '["1", "0"]'
    row, reasons = normalize_event(candidate, "abc")
    assert row is None
    assert "TERMINAL_WINNER_COUNT_NOT_ONE" in reasons
