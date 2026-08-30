"""ECMWF Open Data index inventory and immutable subset retrieval."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.request import Request, urlopen

from ecmwf.opendata import Client

PARAMETERS = ("2t", "mx2t3", "mn2t3")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def index_url(run_date: str, cycle: int, stream: str, step: int) -> str:
    if stream not in {"oper", "enfo"}:
        raise ValueError("unsupported ECMWF stream")
    kind = "fc" if stream == "oper" else "ef"
    return (
        f"https://data.ecmwf.int/forecasts/{run_date}/{cycle:02d}z/ifs/0p25/{stream}/"
        f"{run_date}{cycle:02d}0000-{step}h-{stream}-{kind}.index"
    )


def fetch_index(url: str, destination: Path, timeout: float = 60.0) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"immutable destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    requested_at = utc_iso()
    started = monotonic()
    request = Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        headers = dict(response.headers.items())
        status = response.status
    destination.write_bytes(raw)
    return {
        "url": url,
        "http_status": status,
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "http_last_modified": headers.get("Last-Modified"),
        "http_etag": headers.get("ETag"),
        "local_path": str(destination),
    }


def inventory_index(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    selected = [row for row in rows if row.get("param") in PARAMETERS]
    counts = Counter((row.get("type"), row.get("param")) for row in selected)
    members = sorted(
        {int(row["number"]) for row in selected if row.get("type") == "pf" and "number" in row}
    )
    return {
        "row_count": len(rows),
        "selected_row_count": len(selected),
        "type_parameter_counts": {
            f"{kind}:{parameter}": count
            for (kind, parameter), count in sorted(counts.items())
        },
        "perturbed_members": members,
        "perturbed_member_count": len(members),
        "selected_range_bytes": sum(int(row["_length"]) for row in selected),
        "all_selected_have_ranges": all(
            isinstance(row.get("_offset"), int) and isinstance(row.get("_length"), int)
            for row in selected
        ),
    }


def retrieve_subset(
    run_date: str,
    cycle: int,
    stream: str,
    forecast_type: str,
    step: int,
    destination: Path,
    number: list[int] | None = None,
) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"immutable destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = {
        "date": run_date,
        "time": cycle,
        "stream": stream,
        "type": forecast_type,
        "step": step,
        "param": list(PARAMETERS),
    }
    if number is not None:
        request["number"] = number
    requested_at = utc_iso()
    started = monotonic()
    result = Client(source="ecmwf", model="ifs").retrieve(request, str(destination))
    raw = destination.read_bytes()
    resolved = result.datetime
    if isinstance(resolved, datetime):
        resolved = [resolved]
    return {
        "request": request,
        "resolved_run_times": [value.isoformat() + "Z" for value in resolved],
        "requested_at_utc": requested_at,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "grib_message_count": raw.count(b"GRIB"),
        "starts_with_grib": raw.startswith(b"GRIB"),
        "ends_with_7777": raw.endswith(b"7777"),
        "local_path": str(destination),
    }
