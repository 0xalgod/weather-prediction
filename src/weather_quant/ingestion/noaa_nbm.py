"""Read-only NOAA NBM public-object retrieval and text-product inventory."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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


def extract_station_block(content: bytes, station_code: str) -> bytes:
    """Extract one complete NBP station block from a full object or byte-range payload."""

    text = content.decode("ascii", errors="strict")
    block, _ = _station_block(text, station_code)
    return block.encode("ascii")


def download_station_range(
    url: str,
    station_code: str,
    byte_start: int,
    byte_end: int,
    destination: Path,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Download a bounded range and persist only one complete station block."""

    if byte_start < 0 or byte_end < byte_start:
        raise ValueError("invalid byte range")
    if destination.exists():
        raise FileExistsError(f"immutable destination exists: {destination}")
    requested_at = utc_iso()
    started = monotonic()
    request = Request(
        url,
        headers={
            "User-Agent": "weather-quant-research/0.1",
            "Range": f"bytes={byte_start}-{byte_end}",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
        headers = dict(response.headers.items())
        status = response.status
    if status != 206:
        raise ValueError(f"server did not honor byte range: HTTP {status}")
    block = extract_station_block(payload, station_code)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(block)
    return {
        "source": "noaa_nbm_aws_public_range",
        "url": url,
        "station_code": station_code,
        "http_status": status,
        "requested_range": [byte_start, byte_end],
        "content_range": headers.get("Content-Range"),
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "range_byte_count": len(payload),
        "range_sha256": hashlib.sha256(payload).hexdigest(),
        "station_block_byte_count": len(block),
        "station_block_sha256": hashlib.sha256(block).hexdigest(),
        "http_last_modified": headers.get("Last-Modified"),
        "http_etag": headers.get("ETag"),
        "local_path": str(destination),
    }


def publication_is_admissible(last_modified: str, decision_time_utc: str) -> bool:
    """Return whether an HTTP publication timestamp was available by decision time."""

    published = parsedate_to_datetime(last_modified).astimezone(timezone.utc)
    decision = datetime.fromisoformat(decision_time_utc.replace("Z", "+00:00"))
    if decision.tzinfo is None:
        raise ValueError("decision time must be timezone-aware")
    return published <= decision.astimezone(timezone.utc)


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


def _station_block(text: str, station_code: str) -> tuple[str, str]:
    pattern = re.compile(
        rf"(?m)^ {re.escape(station_code)}\s+NBM V(?P<version>[0-9.]+) NBP GUIDANCE.*$"
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected one {station_code} NBP block, found {len(matches)}")
    match = matches[0]
    next_header = re.search(r"(?m)^ [A-Z0-9]{4}\s+NBM V", text[match.end() :])
    end = match.end() + next_header.start() if next_header else len(text)
    return text[match.start() : end], match.group("version")


def parse_station_maxt(path: Path, station_code: str, model_run_time_utc: str) -> dict[str, Any]:
    """Parse NBP fixed-width MaxT distribution rows for one exact station block."""

    text = path.read_text(encoding="ascii", errors="strict")
    block, version = _station_block(text, station_code)
    required = ("FHR", "TXNMN", "TXNSD", "TXNP1", "TXNP2", "TXNP5", "TXNP7", "TXNP9")
    rows = {}
    for marker in required:
        match = re.search(rf"(?m)^ {marker}\s+(.+)$", block)
        if match is None:
            raise ValueError(f"missing {marker} in {station_code} block")
        tokens = re.findall(r"-?\d+|M", match.group(1).replace("|", " "))
        rows[marker] = [None if token == "M" else int(token) for token in tokens]
    lengths = {len(values) for values in rows.values()}
    if len(lengths) != 1 or not lengths or 0 in lengths:
        raise ValueError("NBP row lengths do not agree")
    run_time = datetime.fromisoformat(model_run_time_utc.replace("Z", "+00:00"))
    if run_time.tzinfo is None:
        raise ValueError("model run time must be timezone-aware")
    records = []
    for index, forecast_hour in enumerate(rows["FHR"]):
        if forecast_hour is None:
            raise ValueError("forecast hour cannot be missing")
        valid_time = run_time + timedelta(hours=forecast_hour)
        if valid_time.hour != 0:
            continue
        values = {
            "mean_f": rows["TXNMN"][index],
            "standard_deviation_f": rows["TXNSD"][index],
            "p10_f": rows["TXNP1"][index],
            "p25_f": rows["TXNP2"][index],
            "p50_f": rows["TXNP5"][index],
            "p75_f": rows["TXNP7"][index],
            "p90_f": rows["TXNP9"][index],
        }
        percentiles = [values[key] for key in ("p10_f", "p25_f", "p50_f", "p75_f", "p90_f")]
        calibrated = [value for value in percentiles if value is not None]
        if calibrated != sorted(calibrated):
            raise ValueError("MaxT percentiles are not monotonic")
        records.append(
            {
                "station_code": station_code,
                "nbm_version": version,
                "model_run_time_utc": model_run_time_utc,
                "forecast_hour": forecast_hour,
                "valid_time_utc": valid_time.isoformat().replace("+00:00", "Z"),
                "temperature_kind": "MAXIMUM",
                "temperature_unit": "F",
                **values,
            }
        )
    if not records:
        raise ValueError("station block contains no 00Z-valid MaxT rows")
    return {"station_code": station_code, "nbm_version": version, "records": records}
