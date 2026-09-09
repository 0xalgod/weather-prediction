"""NOAA NCEI Local Climatological Data v2 parsing helpers."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any


def parse_float(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_lcdv2_sod(content: bytes) -> list[dict[str, Any]]:
    """Return normalized Summary-of-Day rows from one LCDv2 annual CSV."""
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows: list[dict[str, Any]] = []
    for source in reader:
        if source.get("REPORT_TYPE", "").strip() != "SOD":
            continue
        timestamp = datetime.fromisoformat(source["DATE"])
        rows.append(
            {
                "station": source.get("STATION", "").strip(),
                "date": timestamp.date().isoformat(),
                "latitude": parse_float(source.get("LATITUDE", "")),
                "longitude": parse_float(source.get("LONGITUDE", "")),
                "elevation_m": parse_float(source.get("ELEVATION", "")),
                "name": source.get("NAME", "").strip(),
                "report_type": "SOD",
                "source_code": source.get("SOURCE", "").strip(),
                "daily_maximum_dry_bulb_c": parse_float(
                    source.get("DailyMaximumDryBulbTemperature", "")
                ),
            }
        )
    return rows


def parse_lcdv2_hourly(content: bytes) -> list[dict[str, Any]]:
    """Return normalized hourly observation rows, preserving NOAA local-standard timestamps."""
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    fields = {
        "dry_bulb_c": "HourlyDryBulbTemperature",
        "dew_point_c": "HourlyDewPointTemperature",
        "relative_humidity_pct": "HourlyRelativeHumidity",
        "wind_speed_ms": "HourlyWindSpeed",
        "wind_gust_ms": "HourlyWindGustSpeed",
        "sea_level_pressure_hpa": "HourlySeaLevelPressure",
        "station_pressure_hpa": "HourlyStationPressure",
        "visibility_km": "HourlyVisibility",
        "precipitation_mm": "HourlyPrecipitation",
    }
    rows: list[dict[str, Any]] = []
    for source in reader:
        report_type = source.get("REPORT_TYPE", "").strip()
        if report_type == "SOD" or not any(
            source.get(column, "").strip() for column in fields.values()
        ):
            continue
        values = {name: parse_float(source.get(column, "")) for name, column in fields.items()}
        rows.append(
            {
                "station": source.get("STATION", "").strip(),
                "timestamp_local_standard": datetime.fromisoformat(source["DATE"]).isoformat(),
                "date_local_standard": datetime.fromisoformat(source["DATE"]).date().isoformat(),
                "hour_local_standard": datetime.fromisoformat(source["DATE"]).hour,
                "latitude": parse_float(source.get("LATITUDE", "")),
                "longitude": parse_float(source.get("LONGITUDE", "")),
                "name": source.get("NAME", "").strip(),
                "report_type": report_type,
                **values,
            }
        )
    return rows


def dates_inclusive(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end must be on or after start")
    return [date.fromordinal(day) for day in range(start.toordinal(), end.toordinal() + 1)]


def celsius_to_fahrenheit(value: float) -> float:
    return value * 9.0 / 5.0 + 32.0
