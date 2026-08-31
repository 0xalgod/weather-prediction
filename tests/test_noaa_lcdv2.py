from datetime import date
from pathlib import Path

import pytest

from weather_quant.ingestion.noaa_lcdv2 import (
    celsius_to_fahrenheit,
    dates_inclusive,
    parse_lcdv2_sod,
)

FIXTURE = Path(__file__).parent / "fixtures" / "noaa_lcdv2_sample.csv"


def test_parse_lcdv2_sod_filters_and_normalizes() -> None:
    rows = parse_lcdv2_sod(FIXTURE.read_bytes())
    assert len(rows) == 2
    assert rows[0]["station"] == "USW00094846"
    assert rows[0]["date"] == "2026-06-05"
    assert rows[0]["daily_maximum_dry_bulb_c"] == 27.5
    assert rows[1]["daily_maximum_dry_bulb_c"] is None


def test_dates_inclusive_and_invalid_window() -> None:
    assert dates_inclusive(date(2026, 1, 1), date(2026, 1, 2)) == [
        date(2026, 1, 1),
        date(2026, 1, 2),
    ]
    with pytest.raises(ValueError):
        dates_inclusive(date(2026, 1, 2), date(2026, 1, 1))


def test_celsius_to_fahrenheit() -> None:
    assert celsius_to_fahrenheit(27.5) == pytest.approx(81.5)
