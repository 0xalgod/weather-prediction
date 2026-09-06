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
