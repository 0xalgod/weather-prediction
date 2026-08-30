#!/usr/bin/env python3
"""Measure deterministic monthly and model-boundary NBM object coverage."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from time import monotonic
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from weather_quant.ingestion.noaa_nbm import probabilistic_text_url

BOUNDARY_DATES = (
    "20240514",
    "20240515",
    "20240516",
    "20250518",
    "20250519",
    "20250520",
    "20260504",
    "20260505",
    "20260506",
    "20260727",
    "20260728",
    "20260729",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-month", required=True, help="YYYY-MM")
    parser.add_argument("--end-month", required=True, help="YYYY-MM")
    parser.add_argument("--cycle", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def month_starts(start_month: str, end_month: str) -> list[str]:
    current = date.fromisoformat(start_month + "-01")
    end = date.fromisoformat(end_month + "-01")
    dates = []
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return dates


def head(url: str) -> dict:
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started = monotonic()
    try:
        with urlopen(Request(url, method="HEAD"), timeout=30) as response:
            return {
                "http_status": response.status,
                "content_length": int(response.headers["Content-Length"]),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
                "observed_at_utc": observed_at,
                "latency_seconds": monotonic() - started,
            }
    except HTTPError as error:
        return {
            "http_status": error.code,
            "content_length": None,
            "last_modified": None,
            "etag": None,
            "observed_at_utc": observed_at,
            "latency_seconds": monotonic() - started,
        }


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError("coverage output must be immutable")
    monthly = month_starts(args.start_month, args.end_month)
    start = monthly[0]
    end = monthly[-1]
    boundaries = [value for value in BOUNDARY_DATES if start <= value <= end[:6] + "31"]
    dates = sorted(set(monthly + boundaries))
    records = []
    for run_date in dates:
        url = probabilistic_text_url(run_date, args.cycle)
        records.append(
            {
                "run_date": run_date,
                "cycle_utc": args.cycle,
                "sample_type": [
                    label
                    for label, collection in (
                        ("MONTH_START", monthly),
                        ("MODEL_BOUNDARY", boundaries),
                    )
                    if run_date in collection
                ],
                "url": url,
                **head(url),
            }
        )
    available = [record for record in records if record["http_status"] == 200]
    output = {
        "schema_version": "0.1.0",
        "start_month": args.start_month,
        "end_month": args.end_month,
        "cycle_utc": args.cycle,
        "sample_count": len(records),
        "available_count": len(available),
        "coverage_rate": len(available) / len(records),
        "monthly_sample_count": len(monthly),
        "boundary_sample_count": len(boundaries),
        "total_available_bytes": sum(record["content_length"] for record in available),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in output if key != "records"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
