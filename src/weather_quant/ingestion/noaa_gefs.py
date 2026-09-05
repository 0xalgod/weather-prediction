"""Read-only NOAA GEFS operational archive inventory and GRIB range retrieval."""

from __future__ import annotations

import hashlib
import math
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

GEFS_AWS_BASE = "https://noaa-gefs-pds.s3.amazonaws.com"
REQUIRED_FIELDS = ("TMP", "TMAX", "TMIN")
MAX_WINDOW_PATTERN = re.compile(r"^(\d+)-(\d+) hour max fcst$")
S3_XML_NAMESPACE = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def member_names() -> list[str]:
    return ["gec00", *(f"gep{number:02d}" for number in range(1, 31))]


def parse_s3_listing(payload: bytes) -> dict[str, Any]:
    """Parse one public S3 ListObjectsV2 page with namespace enforcement."""

    root = ET.fromstring(payload)
    contents = []
    for item in root.findall("s3:Contents", S3_XML_NAMESPACE):
        contents.append(
            {
                "key": item.findtext("s3:Key", namespaces=S3_XML_NAMESPACE),
                "last_modified": item.findtext(
                    "s3:LastModified", namespaces=S3_XML_NAMESPACE
                ),
                "etag": item.findtext("s3:ETag", namespaces=S3_XML_NAMESPACE),
                "size": int(
                    item.findtext("s3:Size", namespaces=S3_XML_NAMESPACE) or "0"
                ),
            }
        )
    truncated = root.findtext("s3:IsTruncated", namespaces=S3_XML_NAMESPACE)
    token = root.findtext("s3:NextContinuationToken", namespaces=S3_XML_NAMESPACE)
    if truncated == "true" and not token:
        raise ValueError("truncated S3 listing has no continuation token")
    return {
        "objects": contents,
        "is_truncated": truncated == "true",
        "next_continuation_token": token,
    }


def list_run_prefix(
    run_date: str, cycle: int = 0, timeout: float = 60.0
) -> dict[str, Any]:
    """List every GEFS object under one run/product prefix with page provenance."""

    if len(run_date) != 8 or not run_date.isdigit() or cycle not in {0, 6, 12, 18}:
        raise ValueError("invalid GEFS run date or cycle")
    prefix = f"gefs.{run_date}/{cycle:02d}/atmos/pgrb2sp25/"
    token = None
    objects = []
    pages = []
    while True:
        query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            query["continuation-token"] = token
        url = f"{GEFS_AWS_BASE}/?{urlencode(query)}"
        request = Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
            status = response.status
        parsed = parse_s3_listing(payload)
        pages.append(
            {
                "url": url,
                "http_status": status,
                "byte_count": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        objects.extend(parsed["objects"])
        if not parsed["is_truncated"]:
            break
        token = parsed["next_continuation_token"]
    return {"prefix": prefix, "pages": pages, "objects": objects}


def local_day_tmax_steps(target_date: date, timezone_name: str) -> dict[str, Any]:
    """Select canonical 6-hour GEFS TMAX steps overlapping one station-local day."""

    run_time = datetime.combine(
        target_date - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    target_start, target_end = local_day_utc(target_date, timezone_name)
    candidates = [
        (step, run_time + timedelta(hours=step - 6), run_time + timedelta(hours=step))
        for step in range(6, 61, 6)
    ]
    selected = [
        (step, start, end)
        for step, start, end in candidates
        if start < target_end and end > target_start
    ]
    coverage = window_coverage(
        target_start, target_end, [(start, end) for _, start, end in selected]
    )
    interior_steps = [
        step
        for step, start, end in selected
        if start >= target_start and end <= target_end
    ]
    return {
        "target_start_utc": target_start.isoformat().replace("+00:00", "Z"),
        "target_end_utc": target_end.isoformat().replace("+00:00", "Z"),
        "overlap_steps": [step for step, _, _ in selected],
        "interior_steps": interior_steps,
        **coverage,
    }


def kelvin_to_fahrenheit(value: float) -> float:
    return (value - 273.15) * 9 / 5 + 32


def coordinate_delta_degrees(
    observed_latitude: float,
    observed_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    observed_lon_signed = (
        observed_longitude - 360 if observed_longitude > 180 else observed_longitude
    )
    return math.hypot(
        observed_latitude - target_latitude,
        observed_lon_signed - target_longitude,
    )


def decode_nearest_tmax(
    path: Path, latitude: float, longitude: float
) -> dict[str, Any]:
    """Decode one GRIB2 TMAX message at the nearest grid point."""

    from eccodes import (  # type: ignore[import-not-found]
        codes_get,
        codes_grib_find_nearest,
        codes_grib_new_from_file,
        codes_release,
    )

    with path.open("rb") as source:
        gid = codes_grib_new_from_file(source)
        if gid is None:
            raise ValueError("GRIB file has no message")
        try:
            short_name = codes_get(gid, "shortName")
            level = codes_get(gid, "level")
            step_range = str(codes_get(gid, "stepRange"))
            units = codes_get(gid, "units")
            nearest = codes_grib_find_nearest(
                gid, latitude, longitude, npoints=1
            )[0]
            if codes_grib_new_from_file(source) is not None:
                raise ValueError("expected exactly one GRIB message")
        finally:
            codes_release(gid)
    if short_name != "tmax" or units != "K" or level != 2:
        raise ValueError("decoded message is not 2 m TMAX in Kelvin")
    value_k = float(nearest["value"])
    return {
        "short_name": short_name,
        "level_m": level,
        "step_range": step_range,
        "units": units,
        "grid_latitude": float(nearest["lat"]),
        "grid_longitude": float(nearest["lon"]),
        "distance_km": float(nearest["distance"]),
        "coordinate_delta_degrees": coordinate_delta_degrees(
            float(nearest["lat"]),
            float(nearest["lon"]),
            latitude,
            longitude,
        ),
        "temperature_k": value_k,
        "temperature_f": kelvin_to_fahrenheit(value_k),
    }


def object_url(run_date: str, cycle: int, member: str, step: int) -> str:
    if len(run_date) != 8 or not run_date.isdigit() or cycle not in {0, 6, 12, 18}:
        raise ValueError("invalid GEFS run date or cycle")
    if member not in member_names() or step < 0 or step > 240 or step % 3:
        raise ValueError("invalid GEFS member or forecast step")
    filename = f"{member}.t{cycle:02d}z.pgrb2s.0p25.f{step:03d}"
    return (
        f"{GEFS_AWS_BASE}/gefs.{run_date}/{cycle:02d}/atmos/pgrb2sp25/{filename}"
    )


def aggregate_object_url(run_date: str, cycle: int, product: str, step: int) -> str:
    if len(run_date) != 8 or not run_date.isdigit() or cycle not in {0, 6, 12, 18}:
        raise ValueError("invalid GEFS run date or cycle")
    if product not in {"geavg", "gespr"} or step < 0 or step > 240 or step % 3:
        raise ValueError("invalid GEFS aggregate product or forecast step")
    filename = f"{product}.t{cycle:02d}z.pgrb2s.0p25.f{step:03d}"
    return (
        f"{GEFS_AWS_BASE}/gefs.{run_date}/{cycle:02d}/atmos/pgrb2sp25/{filename}"
    )


def parse_index(text: str, content_length: int) -> dict[str, Any]:
    rows = []
    lines = [line for line in text.splitlines() if line]
    for position, line in enumerate(lines):
        fields = line.split(":")
        if len(fields) < 7:
            raise ValueError(f"malformed GEFS index row: {line}")
        offset = int(fields[1])
        end = (
            int(lines[position + 1].split(":")[1]) - 1
            if position + 1 < len(lines)
            else content_length - 1
        )
        rows.append(
            {
                "message": int(fields[0]),
                "offset": offset,
                "end": end,
                "length": end - offset + 1,
                "run": fields[2],
                "parameter": fields[3],
                "level": fields[4],
                "forecast_window": fields[5],
                "ensemble": fields[6],
            }
        )
    selected = [
        row
        for row in rows
        if row["parameter"] in REQUIRED_FIELDS and row["level"] == "2 m above ground"
    ]
    counts = {
        field: sum(row["parameter"] == field for row in selected)
        for field in REQUIRED_FIELDS
    }
    return {
        "row_count": len(rows),
        "selected_row_count": len(selected),
        "required_field_counts": counts,
        "selected_range_bytes": sum(row["length"] for row in selected),
        "selected_rows": selected,
    }


def summarize_index(text: str) -> dict[str, Any]:
    """Summarize required fields without retrieving the much larger GRIB object."""
    rows = []
    for line in (line for line in text.splitlines() if line):
        fields = line.split(":")
        if len(fields) < 7:
            raise ValueError(f"malformed GEFS index row: {line}")
        rows.append(
            {
                "parameter": fields[3],
                "level": fields[4],
                "forecast_window": fields[5],
                "ensemble": fields[6],
            }
        )
    selected = [
        row
        for row in rows
        if row["parameter"] in REQUIRED_FIELDS and row["level"] == "2 m above ground"
    ]
    return {
        "row_count": len(rows),
        "selected_row_count": len(selected),
        "required_field_counts": {
            field: sum(row["parameter"] == field for row in selected)
            for field in REQUIRED_FIELDS
        },
        "selected_rows": selected,
    }


def parse_max_window(value: str) -> tuple[int, int]:
    match = MAX_WINDOW_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"invalid GEFS maximum window: {value}")
    start, end = (int(part) for part in match.groups())
    if start >= end:
        raise ValueError(f"non-positive GEFS maximum window: {value}")
    return start, end


def local_day_utc(local_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_start = datetime.combine(local_date, datetime.min.time(), tzinfo=zone)
    local_end = datetime.combine(local_date + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def window_coverage(
    target_start: datetime,
    target_end: datetime,
    windows: list[tuple[datetime, datetime]],
) -> dict[str, Any]:
    if target_start.tzinfo is None or target_end.tzinfo is None:
        raise ValueError("target datetimes must be timezone-aware")
    selected = sorted(
        (start, end)
        for start, end in windows
        if start < target_end and end > target_start
    )
    covered_intervals = []
    for start, end in selected:
        clipped = (max(start, target_start), min(end, target_end))
        if clipped[0] < clipped[1]:
            covered_intervals.append(clipped)
    merged = []
    for start, end in covered_intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    covered_seconds = sum((end - start).total_seconds() for start, end in merged)
    target_seconds = (target_end - target_start).total_seconds()
    outside_seconds = sum(
        max(0.0, (min(end, target_start) - start).total_seconds())
        + max(0.0, (end - max(start, target_end)).total_seconds())
        for start, end in selected
    )
    return {
        "target_seconds": target_seconds,
        "covered_seconds": covered_seconds,
        "uncovered_seconds": target_seconds - covered_seconds,
        "outside_local_seconds": outside_seconds,
        "selected_window_count": len(selected),
        "exact_partition": covered_seconds == target_seconds and outside_seconds == 0,
    }


def fetch_index_summary(
    url: str, timeout: float = 30.0, attempts: int = 3
) -> dict[str, Any]:
    """Fetch a GEFS index with bounded retries and explicit failure provenance."""
    index_url = url + ".idx"
    requested_at = utc_iso()
    started = monotonic()
    errors = []
    for attempt in range(1, attempts + 1):
        try:
            request = Request(
                index_url, headers={"User-Agent": "weather-quant-research/0.1"}
            )
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
                headers = dict(response.headers.items())
                status = response.status
            return {
                "url": url,
                "index_url": index_url,
                "requested_at_utc": requested_at,
                "received_at_utc": utc_iso(),
                "retrieval_seconds": monotonic() - started,
                "attempt_count": attempt,
                "http_status": status,
                "index_byte_count": len(raw),
                "index_sha256": hashlib.sha256(raw).hexdigest(),
                "http_last_modified": headers.get("Last-Modified"),
                "http_etag": headers.get("ETag"),
                "inventory": summarize_index(raw.decode("ascii")),
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
        "index_url": index_url,
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "attempt_count": len(errors),
        "http_status": errors[-1].get("status") if errors else None,
        "inventory": None,
        "errors": errors,
    }
def fetch_inventory(url: str, timeout: float = 60.0) -> dict[str, Any]:
    requested_at = utc_iso()
    started = monotonic()
    request = Request(url + ".idx", headers={"User-Agent": "weather-quant-research/0.1"})
    with urlopen(request, timeout=timeout) as response:
        index_raw = response.read()
        index_headers = dict(response.headers.items())
        index_status = response.status
    head = Request(url, method="HEAD", headers={"User-Agent": "weather-quant-research/0.1"})
    with urlopen(head, timeout=timeout) as response:
        content_length = int(response.headers["Content-Length"])
        object_headers = dict(response.headers.items())
        object_status = response.status
    return {
        "url": url,
        "index_url": url + ".idx",
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "http_status": object_status,
        "index_http_status": index_status,
        "object_byte_count": content_length,
        "index_byte_count": len(index_raw),
        "index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "http_last_modified": object_headers.get("Last-Modified"),
        "http_etag": object_headers.get("ETag"),
        "index_http_last_modified": index_headers.get("Last-Modified"),
        "inventory": parse_index(index_raw.decode("ascii"), content_length),
    }


def download_selected_ranges(
    inventory: dict[str, Any], destination: Path, timeout: float = 60.0
) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"immutable destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    byte_count = 0
    statuses = []
    requested_at = utc_iso()
    started = monotonic()
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".part",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as output:
            for row in inventory["inventory"]["selected_rows"]:
                request = Request(
                    inventory["url"],
                    headers={
                        "User-Agent": "weather-quant-research/0.1",
                        "Range": f"bytes={row['offset']}-{row['end']}",
                    },
                )
                with urlopen(request, timeout=timeout) as response:
                    raw = response.read()
                    statuses.append(response.status)
                valid = (
                    len(raw) == row["length"]
                    and raw.startswith(b"GRIB")
                    and raw.endswith(b"7777")
                )
                if not valid:
                    raise ValueError("GEFS range failed length or GRIB integrity contract")
                output.write(raw)
                digest.update(raw)
                byte_count += len(raw)
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "url": inventory["url"],
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "range_http_statuses": statuses,
        "grib_message_count": len(statuses),
        "byte_count": byte_count,
        "sha256": digest.hexdigest(),
        "starts_with_grib": destination.read_bytes().startswith(b"GRIB"),
        "ends_with_7777": destination.read_bytes().endswith(b"7777"),
        "local_path": str(destination),
    }
