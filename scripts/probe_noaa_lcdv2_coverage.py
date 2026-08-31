#!/usr/bin/env python3
"""Measure the pre-registered KORD NOAA LCDv2 observation coverage gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from weather_quant.ingestion.noaa_lcdv2 import (
    celsius_to_fahrenheit,
    dates_inclusive,
    parse_lcdv2_sod,
)

BASE_URL = "https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access"
EXPECTED_STATION = "USW00094846"
EXPECTED_NAME = "CHICAGO OHARE INTERNATIONAL AIRPORT, IL US"
EXPECTED_LATITUDE = 41.96019
EXPECTED_LONGITUDE = -87.93162


def fetch(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read(), {
            "etag": response.headers.get("ETag", ""),
            "last_modified": response.headers.get("Last-Modified", ""),
            "content_type": response.headers.get("Content-Type", ""),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 8, 31))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 8, 30))
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/data_quality/EXP-20260831-phase5-kord-lcdv2-observation-coverage.json"),
    )
    args = parser.parse_args()

    raw_dir = Path("data/raw/noaa_lcdv2") / f"run={args.run_id}"
    raw_dir.mkdir(parents=True, exist_ok=False)
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    all_rows: list[dict[str, Any]] = []
    objects = []
    for year in range(args.start.year, args.end.year + 1):
        filename = f"LCD_{EXPECTED_STATION}_{year}.csv"
        url = f"{BASE_URL}/{year}/{filename}"
        content, headers = fetch(url)
        (raw_dir / filename).write_bytes(content)
        rows = parse_lcdv2_sod(content)
        all_rows.extend(rows)
        last_sod_date = max(row["date"] for row in rows) if rows else None
        last_modified = headers["last_modified"]
        lag_days = None
        if last_sod_date and last_modified:
            lag_days = (
                parsedate_to_datetime(last_modified).date() - date.fromisoformat(last_sod_date)
            ).days
        objects.append(
            {
                "url": url,
                "filename": filename,
                "retrieved_at_utc": retrieved_at,
                "byte_count": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "headers": headers,
                "sod_row_count": len(rows),
                "last_sod_date": last_sod_date,
                "last_modified_to_last_sod_calendar_days": lag_days,
            }
        )

    expected_dates = dates_inclusive(args.start, args.end)
    expected_set = {item.isoformat() for item in expected_dates}
    window_rows = [row for row in all_rows if row["date"] in expected_set]
    counts = Counter(row["date"] for row in window_rows)
    represented = set(counts)
    missing_dates = sorted(expected_set - represented)
    duplicate_dates = sorted(item for item, count in counts.items() if count > 1)
    non_null_dates = {
        row["date"] for row in window_rows if row["daily_maximum_dry_bulb_c"] is not None
    }
    identity_failures = [
        row
        for row in window_rows
        if row["station"] != EXPECTED_STATION
        or row["name"] != EXPECTED_NAME
        or row["latitude"] is None
        or row["longitude"] is None
        or abs(row["latitude"] - EXPECTED_LATITUDE) > 0.01
        or abs(row["longitude"] - EXPECTED_LONGITUDE) > 0.01
    ]

    sentinel = next((row for row in window_rows if row["date"] == "2026-06-05"), None)
    sentinel_max_c = sentinel["daily_maximum_dry_bulb_c"] if sentinel else None
    sentinel_max_f = celsius_to_fahrenheit(sentinel_max_c) if sentinel_max_c is not None else None
    sentinel_bucket_match = sentinel_max_f is not None and sentinel_max_f >= 68.0

    date_coverage = len(represented) / len(expected_dates)
    maximum_coverage = len(non_null_dates) / len(expected_dates)
    gate = (
        date_coverage >= 0.99
        and maximum_coverage >= 0.99
        and not duplicate_dates
        and not identity_failures
    )
    artifact = {
        "schema_version": "0.1.0",
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "KORD NOAA LCDv2 365-day observation coverage",
        "generated_at_utc": retrieved_at,
        "locked_contract": {
            "start_date": args.start.isoformat(),
            "end_date": args.end.isoformat(),
            "expected_date_count": len(expected_dates),
            "station": EXPECTED_STATION,
            "icao": "KORD",
            "timezone": "America/Chicago",
            "date_coverage_minimum": 0.99,
            "non_null_daily_maximum_coverage_minimum": 0.99,
            "duplicate_daily_summary_maximum": 0,
            "identity_rate_required": 1.0,
        },
        "objects": objects,
        "metrics": {
            "terminal_transport_failure_count": 0,
            "represented_date_count": len(represented),
            "date_coverage": date_coverage,
            "non_null_daily_maximum_date_count": len(non_null_dates),
            "non_null_daily_maximum_coverage": maximum_coverage,
            "missing_date_count": len(missing_dates),
            "missing_dates": missing_dates,
            "duplicate_date_count": len(duplicate_dates),
            "duplicate_dates": duplicate_dates,
            "identity_failure_count": len(identity_failures),
            "admitted_row_count": len(window_rows),
            "daily_maximum_c_min": min(
                row["daily_maximum_dry_bulb_c"]
                for row in window_rows
                if row["daily_maximum_dry_bulb_c"] is not None
            ),
            "daily_maximum_c_max": max(
                row["daily_maximum_dry_bulb_c"]
                for row in window_rows
                if row["daily_maximum_dry_bulb_c"] is not None
            ),
        },
        "settlement_sentinel": {
            "event_id": "553903",
            "market_date_local": "2026-06-05",
            "terminal_winner_bucket": "68°F or higher",
            "wunderground_current_high": {"value": 27, "unit": "C"},
            "lcdv2_daily_maximum_c": sentinel_max_c,
            "lcdv2_daily_maximum_f": sentinel_max_f,
            "lcdv2_terminal_bucket_consistent": sentinel_bucket_match,
            "interpretation": "FORENSIC_CONSISTENCY_ONLY",
        },
        "semantics": {
            "provider": "NOAA NCEI",
            "dataset": "Local Climatological Data v2",
            "field": "DailyMaximumDryBulbTemperature",
            "unit": "C",
            "report_type": "SOD",
            "role": "INDEPENDENT_FINAL_DIAGNOSTIC_ONLY",
            "settlement_source": "Wunderground KORD",
            "historical_freeze_as_of_status": "HISTORICAL_FREEZE_AS_OF_UNRESOLVED",
        },
        "coverage_gate_passed": gate,
        "raw_local_directory": str(raw_dir),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
