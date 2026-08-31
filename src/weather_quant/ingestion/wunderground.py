"""Read-only Wunderground daily-history retrieval and semantic parsing."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

AIRPORT_PATTERN = re.compile(r"<airport-body\s+([^>]+)>")
ATTRIBUTE_PATTERN = re.compile(r'data-([\w-]+)="([^"]*)"')
STATION_PATTERN = re.compile(r'<span class="station">.*?</span>([^<]+)</span>', re.S)
HIGH_PATTERN = re.compile(
    r'<div class="high-low-item high">.*?<div class="value">\s*(-?\d+)°([CF])\s*</div>',
    re.S,
)
CHART_PATTERN = re.compile(
    r'<script type="application/json" class="chart-data">(.*?)</script>', re.S
)


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def daily_url(base_url: str, requested_date: str) -> str:
    parsed = datetime.strptime(requested_date, "%Y-%m-%d").date()
    return f"{base_url.rstrip('/')}/date/{parsed.year}-{parsed.month}-{parsed.day}"


def parse_daily_page(page: str) -> dict[str, Any]:
    airport = AIRPORT_PATTERN.search(page)
    station = STATION_PATTERN.search(page)
    high = HIGH_PATTERN.search(page)
    chart = CHART_PATTERN.search(page)
    attributes = dict(ATTRIBUTE_PATTERN.findall(airport.group(1))) if airport else {}
    observations = json.loads(html.unescape(chart.group(1))) if chart else []
    temperatures = [row.get("temp") for row in observations if row.get("temp") is not None]
    return {
        "station_code": attributes.get("icao-code"),
        "station_name": html.unescape(station.group(1)).strip() if station else None,
        "timezone": attributes.get("time-zone"),
        "page_date": attributes.get("date"),
        "daily_high": int(high.group(1)) if high else None,
        "temperature_unit": high.group(2) if high else None,
        "observation_count": len(observations),
        "observation_temperature_count": len(temperatures),
        "observation_temperature_max": max(temperatures) if temperatures else None,
        "observations": observations,
    }


def fetch_daily_page(url: str, timeout: float = 30.0, attempts: int = 3) -> dict[str, Any]:
    requested_at = utc_iso()
    started = monotonic()
    errors = []
    for attempt in range(1, attempts + 1):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "text/html",
                    "User-Agent": "weather-quant-research/0.1",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
                headers = dict(response.headers.items())
                status = response.status
            return {
                "url": url,
                "requested_at_utc": requested_at,
                "received_at_utc": utc_iso(),
                "retrieval_seconds": monotonic() - started,
                "attempt_count": attempt,
                "http_status": status,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "http_last_modified": headers.get("Last-Modified"),
                "http_etag": headers.get("ETag"),
                "raw": raw,
                "errors": errors,
            }
        except HTTPError as error:
            errors.append({"attempt": attempt, "kind": "http", "status": error.code})
            if error.code == 404:
                break
        except (URLError, TimeoutError, ConnectionError) as error:
            errors.append({"attempt": attempt, "kind": "transport", "detail": str(error)})
        if attempt < attempts:
            time.sleep(0.25 * attempt)
    return {
        "url": url,
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "attempt_count": len(errors),
        "http_status": errors[-1].get("status") if errors else None,
        "raw": None,
        "errors": errors,
    }
