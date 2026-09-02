"""Safe analysis helpers for the NOAA WRH time-series client surface."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SCRIPT_PATTERN = re.compile(r'<script[^>]+src=["\']([^"\']+)', re.I)
URL_PATTERN = re.compile(r"https://[A-Za-z0-9._-]+(?:/[A-Za-z0-9_?&=+|.,${}'/-]*)?")


def analyze_wrh_surface(page: str, client_script: str, credential_script: str) -> dict[str, Any]:
    """Describe data dependencies without returning credential material."""
    script_sources = SCRIPT_PATTERN.findall(page)
    urls = sorted(set(URL_PATTERN.findall(client_script)))
    data_origins = sorted(
        {
            f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for url in urls
            if "stations/timeseries" in url
        }
    )
    return {
        "script_sources": script_sources,
        "timeseries_endpoint_origins": data_origins,
        "official_origin_timeseries_endpoint_count": sum(
            origin.endswith(".noaa.gov") or origin == "https://api.weather.gov"
            for origin in data_origins
        ),
        "third_party_timeseries_endpoint_count": sum(
            not (origin.endswith(".noaa.gov") or origin == "https://api.weather.gov")
            for origin in data_origins
        ),
        "synoptic_timeseries_template_present": any(
            "api.synopticdata.com/v2/stations/timeseries" in url for url in urls
        ),
        "local_timezone_request_present": "obtimezone=local" in client_script,
        "fahrenheit_request_present": "units=temp|F" in client_script,
        "station_parameter_present": "STID=" in client_script,
        "credential_script_referenced": any("apiKey.js" in item for item in script_sources),
        "credential_assignment_present": bool(
            re.search(r"(?:token|key)\s*=", credential_script, re.I)
        ),
        "credential_value_recorded": False,
        "page_warns_preliminary_adjustable": (
            "considered preliminary" in page.lower()
            and "subject to quality control review and adjustment" in page.lower()
        ),
        "page_warns_download_unavailable": "download data feature is not available"
        in page.lower(),
        "static_page_contains_observation_payload": '"OBSERVATIONS"' in page,
    }
