"""Fail-closed station extraction for supported weather resolution URLs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

ICAO = re.compile(r"^[A-Z]{4}$")


def station_code_from_url(value: str) -> str | None:
    """Extract an exact four-letter ICAO code from supported URL shapes."""

    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    candidate = None
    if host in {"www.wunderground.com", "wunderground.com"}:
        parts = [part for part in parsed.path.split("/") if part]
        candidate = parts[-1].upper() if parts else None
    elif host == "www.weather.gov" and parsed.path.rstrip("/") == "/wrh/timeseries":
        values = parse_qs(parsed.query).get("site", [])
        candidate = values[0].upper() if len(values) == 1 else None
    return candidate if candidate and ICAO.fullmatch(candidate) else None
