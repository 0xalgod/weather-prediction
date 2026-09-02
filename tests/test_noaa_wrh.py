from weather_quant.ingestion.noaa_wrh import analyze_wrh_surface


def test_surface_reports_third_party_dependency_without_credential_value() -> None:
    page = """
    <script src="/source/wrh/apiKey.js"></script>
    <script src="/source/wrh/timeseries/obs.js"></script>
    Data is considered preliminary and subject to quality control review and adjustment.
    The download data feature is not available.
    """
    script = (
        "https://api.synopticdata.com/v2/stations/timeseries?"
        "STID='+SITE+'&units=temp|F&obtimezone=local&token='+mesoToken"
    )
    result = analyze_wrh_surface(page, script, "var mesoToken = 'do-not-return';")
    assert result["third_party_timeseries_endpoint_count"] == 1
    assert result["official_origin_timeseries_endpoint_count"] == 0
    assert result["credential_assignment_present"] is True
    assert result["credential_value_recorded"] is False
    assert "do-not-return" not in str(result)
    assert result["static_page_contains_observation_payload"] is False


def test_official_endpoint_is_classified_separately() -> None:
    result = analyze_wrh_surface(
        "<script src='/source/wrh/timeseries/obs.js'></script>",
        "https://api.weather.gov/stations/timeseries?STID=KORD",
        "",
    )
    assert result["official_origin_timeseries_endpoint_count"] == 1
    assert result["third_party_timeseries_endpoint_count"] == 0
