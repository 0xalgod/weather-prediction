"""Read-only NOAA NBM public-object retrieval and text-product inventory."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.request import Request, urlopen

NBM_AWS_BASE = "https://noaa-nbm-grib2-pds.s3.amazonaws.com"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def probabilistic_text_url(run_date: str, cycle: int = 0) -> str:
    if len(run_date) != 8 or not run_date.isdigit() or not 0 <= cycle <= 23:
        raise ValueError("invalid NBM run date or cycle")
    return (
        f"{NBM_AWS_BASE}/blend.{run_date}/{cycle:02d}/text/"
        f"blend_nbptx.t{cycle:02d}z"
    )


def download_public_object(url: str, destination: Path, timeout: float = 60.0) -> dict[str, Any]:
    """Stream one immutable public object to disk with availability provenance."""

    if destination.exists():
        raise FileExistsError(f"immutable destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
    requested_at = utc_iso()
    started = monotonic()
    digest = hashlib.sha256()
    byte_count = 0
    with urlopen(request, timeout=timeout) as response, destination.open("xb") as output:
        headers = dict(response.headers.items())
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            digest.update(chunk)
            byte_count += len(chunk)
        status = response.status
    return {
        "source": "noaa_nbm_aws_public",
        "url": url,
        "http_status": status,
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "byte_count": byte_count,
        "sha256": digest.hexdigest(),
        "http_last_modified": headers.get("Last-Modified"),
        "http_etag": headers.get("ETag"),
        "content_type": headers.get("Content-Type"),
        "local_path": str(destination),
    }


def inspect_probabilistic_text(path: Path, station_code: str) -> dict[str, Any]:
    """Inventory station and MaxT/MinT QMD element markers without modeling values."""

    raw = path.read_bytes()
    text = raw.decode("ascii", errors="replace")
    header_pattern = re.compile(
        rf"(?m)^ {re.escape(station_code)}\s+NBM V(?P<version>[0-9.]+) NBP GUIDANCE.*$"
    )
    station_headers = list(header_pattern.finditer(text))
    station_block = ""
    station_header = None
    version = None
    if station_headers:
        match = station_headers[0]
        next_header = re.search(r"(?m)^ [A-Z0-9]{4}\s+NBM V", text[match.end() :])
        end = match.end() + next_header.start() if next_header else len(text)
        station_block = text[match.start() : end]
        station_header = match.group(0).strip()
        version = match.group("version")
    markers = {
        marker: station_block.count(marker)
        for marker in ("TXNMN", "TXNSD", "TXNP1", "TXNP2", "TXNP5", "TXNP7", "TXNP9")
    }
    return {
        "station_code": station_code,
        "station_occurrence_count": len(station_headers),
        "first_station_offset": station_headers[0].start() if station_headers else None,
        "station_header": station_header,
        "nbm_version": version,
        "element_marker_counts": markers,
        "contains_probabilistic_maxt_markers": all(count > 0 for count in markers.values()),
        "replacement_character_count": text.count("�"),
    }
