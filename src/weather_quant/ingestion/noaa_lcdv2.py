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


def dates_inclusive(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end must be on or after start")
    return [date.fromordinal(day) for day in range(start.toordinal(), end.toordinal() + 1)]


def celsius_to_fahrenheit(value: float) -> float:
    return value * 9.0 / 5.0 + 32.0
