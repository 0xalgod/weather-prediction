from scripts.map_multicity_stations import isd_metadata
from weather_quant.normalization.multicity_station_mapping import station_code_from_url


def test_extracts_supported_station_urls() -> None:
    source = "https://www.wunderground.com/history/daily/us/il/x/KORD"
    assert station_code_from_url(source) == "KORD"
    assert station_code_from_url("https://www.weather.gov/wrh/timeseries?site=klga") == "KLGA"


def test_rejects_unsupported_or_ambiguous_urls() -> None:
    assert station_code_from_url("https://example.com/KORD") is None
    assert station_code_from_url("https://www.weather.gov/wrh/timeseries?site=ABC") is None
    duplicated = "https://www.weather.gov/wrh/timeseries?site=KORD&site=KLGA"
    assert station_code_from_url(duplicated) is None


def test_isd_metadata_enforces_activity_and_coordinates() -> None:
    row = {
        "LAT": "+41.960",
        "LON": "-087.932",
        "BEGIN": "19461001",
        "END": "20250825",
        "STATION NAME": "CHICAGO OHARE",
    }
    accepted = isd_metadata(row, "2026-06-01", 550)
    assert accepted is not None
    assert accepted["activity_semantic"] == "RECENT_ACTIVITY_PROXY"
    assert isd_metadata(row, "2028-06-01", 550) is None
