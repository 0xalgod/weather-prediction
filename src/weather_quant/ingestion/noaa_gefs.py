"""Read-only NOAA GEFS operational archive inventory and GRIB range retrieval."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GEFS_AWS_BASE = "https://noaa-gefs-pds.s3.amazonaws.com"
REQUIRED_FIELDS = ("TMP", "TMAX", "TMIN")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def member_names() -> list[str]:
    return ["gec00", *(f"gep{number:02d}" for number in range(1, 31))]


def object_url(run_date: str, cycle: int, member: str, step: int) -> str:
    if len(run_date) != 8 or not run_date.isdigit() or cycle not in {0, 6, 12, 18}:
        raise ValueError("invalid GEFS run date or cycle")
    if member not in member_names() or step < 0 or step > 240 or step % 3:
        raise ValueError("invalid GEFS member or forecast step")
    filename = f"{member}.t{cycle:02d}z.pgrb2s.0p25.f{step:03d}"
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
    with destination.open("xb") as output:
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
