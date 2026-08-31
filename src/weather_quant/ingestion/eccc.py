"""Environment and Climate Change Canada hourly observation helpers."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ECCC_HOURLY_URL = "https://api.weather.gc.ca/collections/climate-hourly/items"


def hourly_query_url(bbox: str, start_utc: str, end_utc: str, limit: int = 100) -> str:
    query = urlencode(
        {
            "f": "json",
            "limit": limit,
            "bbox": bbox,
            "datetime": f"{start_utc}/{end_utc}",
        }
    )
    return f"{ECCC_HOURLY_URL}?{query}"


def fetch_geojson(url: str, timeout: float = 30.0) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/geo+json",
            "User-Agent": "weather-quant-research/0.1",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        status = response.status
        headers = dict(response.headers.items())
    return {
        "url": url,
        "http_status": status,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "http_last_modified": headers.get("Last-Modified"),
        "raw": raw,
        "document": json.loads(raw),
    }


def station_local_rows(document: dict, climate_identifier: str, local_date: str) -> list[dict]:
    rows = [
        feature["properties"]
        for feature in document.get("features", [])
        if feature["properties"].get("CLIMATE_IDENTIFIER") == climate_identifier
        and feature["properties"].get("LOCAL_DATE", "").startswith(local_date)
    ]
    return sorted(rows, key=lambda row: row["UTC_DATE"])


def round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
