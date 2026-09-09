from weather_quant.ingestion.noaa_lcdv2 import parse_lcdv2_hourly


def test_parse_hourly_excludes_sod_and_preserves_local_standard_timestamp() -> None:
    content = (
        b"STATION,DATE,LATITUDE,LONGITUDE,NAME,REPORT_TYPE,HourlyDryBulbTemperature,HourlyDewPointTemperature,HourlyRelativeHumidity,HourlyWindSpeed,HourlyWindGustSpeed,HourlySeaLevelPressure,HourlyStationPressure,HourlyVisibility,HourlyPrecipitation\n"
        b"USW00094846,2025-01-01T01:51:00,41.96,-87.93,CHICAGO OHARE INTERNATIONAL "
        b"AIRPORT IL US,FM-15,-1.1,-3.3,78,4.1,,1012.3,990.1,16.0,T\n"
        b"USW00094846,2025-01-01T00:00:00,41.96,-87.93,CHICAGO OHARE INTERNATIONAL "
        b"AIRPORT IL US,SOD,1.1,,,,,,,,\n"
    )
    rows = parse_lcdv2_hourly(content)
    assert len(rows) == 1
    assert rows[0]["timestamp_local_standard"] == "2025-01-01T01:51:00"
    assert rows[0]["hour_local_standard"] == 1
    assert rows[0]["dry_bulb_c"] == -1.1
    assert rows[0]["precipitation_mm"] is None
