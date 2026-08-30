#!/usr/bin/env python3
"""Measure a locked daily NBM primary/fallback cycle policy."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from weather_quant.ingestion.noaa_nbm import probabilistic_text_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD inclusive")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD inclusive")
    parser.add_argument("--primary-cycle", type=int, default=1)
    parser.add_argument("--fallback-cycle", action="append", type=int, default=[])
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def dates_inclusive(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    final = date.fromisoformat(end)
    if final < current:
        raise ValueError("end date precedes start date")
    values = []
    while current <= final:
        values.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return values


def probe(run_date: str, cycle: int, retries: int = 2) -> dict:
    url = probabilistic_text_url(run_date, cycle)
    attempts = []
    for attempt in range(retries + 1):
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        started = monotonic()
        try:
            with urlopen(Request(url, method="HEAD"), timeout=30) as response:
                return {
                    "cycle_utc": cycle,
                    "url": url,
                    "http_status": response.status,
                    "content_length": int(response.headers["Content-Length"]),
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag"),
                    "observed_at_utc": observed_at,
                    "latency_seconds": monotonic() - started,
                    "attempt_count": attempt + 1,
                    "transient_errors": attempts,
                }
        except HTTPError as error:
            if error.code == 404:
                return {
                    "cycle_utc": cycle,
                    "url": url,
                    "http_status": 404,
                    "content_length": None,
                    "last_modified": None,
                    "etag": None,
                    "observed_at_utc": observed_at,
                    "latency_seconds": monotonic() - started,
                    "attempt_count": attempt + 1,
                    "transient_errors": attempts,
                }
            attempts.append(f"HTTPError {error.code}")
        except (TimeoutError, URLError) as error:
            attempts.append(f"{type(error).__name__}: {error}")
        if attempt < retries:
            sleep(0.25 * (2**attempt))
    return {
        "cycle_utc": cycle,
        "url": url,
        "http_status": None,
        "content_length": None,
        "last_modified": None,
        "etag": None,
        "observed_at_utc": observed_at,
        "latency_seconds": monotonic() - started,
        "attempt_count": retries + 1,
        "transient_errors": attempts,
    }


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError("daily coverage output must be immutable")
    run_dates = dates_inclusive(args.start_date, args.end_date)
    primary_results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(probe, run_date, args.primary_cycle): run_date
            for run_date in run_dates
        }
        for future in as_completed(futures):
            primary_results[futures[future]] = future.result()
    records = []
    for run_date in run_dates:
        attempts = [primary_results[run_date]]
        selected_cycle = args.primary_cycle if attempts[0]["http_status"] == 200 else None
        if selected_cycle is None and attempts[0]["http_status"] == 404:
            for cycle in args.fallback_cycle:
                result = probe(run_date, cycle)
                attempts.append(result)
                if result["http_status"] == 200:
                    selected_cycle = cycle
                    break
                if result["http_status"] is None:
                    break
        quality = (
            "PRIMARY"
            if selected_cycle == args.primary_cycle
            else "FALLBACK"
            if selected_cycle is not None
            else "UNAVAILABLE"
        )
        records.append(
            {
                "run_date": run_date,
                "selected_cycle_utc": selected_cycle,
                "selection_quality": quality,
                "attempts": attempts,
            }
        )
    primary_count = sum(record["selection_quality"] == "PRIMARY" for record in records)
    fallback_count = sum(record["selection_quality"] == "FALLBACK" for record in records)
    unavailable_count = len(records) - primary_count - fallback_count
    transient_failure_count = sum(
        attempt["http_status"] is None
        for record in records
        for attempt in record["attempts"]
    )
    output = {
        "schema_version": "0.1.0",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "date_count": len(records),
        "primary_cycle_utc": args.primary_cycle,
        "fallback_order_utc": args.fallback_cycle,
        "primary_count": primary_count,
        "fallback_count": fallback_count,
        "unavailable_count": unavailable_count,
        "primary_coverage_rate": primary_count / len(records),
        "policy_coverage_rate": (primary_count + fallback_count) / len(records),
        "transient_failure_count": transient_failure_count,
        "acceptance_criteria": {
            "primary_coverage_rate_min": 0.99,
            "policy_coverage_rate_min": 1.0,
            "transient_failure_count_max": 0,
        },
        "accepted": primary_count / len(records) >= 0.99
        and unavailable_count == 0
        and transient_failure_count == 0,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in output if key != "records"}, indent=2))
    return 0 if output["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
