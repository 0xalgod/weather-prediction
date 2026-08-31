#!/usr/bin/env python3
"""Probe locked Wunderground daily-history pages for station observations."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from weather_quant.ingestion.wunderground import (
    daily_url,
    fetch_daily_page,
    parse_daily_page,
)

OFFSETS = (0, 1, 7, 30, 60, 90, 120, 150, 180, 240, 300, 364)
STATIONS = (
    {
        "city": "Toronto",
        "station_code": "CYYZ",
        "station_name": "Toronto Pearson Intl Airport Station",
        "timezone": "America/Toronto",
        "base_url": "https://www.wunderground.com/history/daily/ca/mississauga/CYYZ",
        "anchor_date": date(2026, 7, 23),
    },
    {
        "city": "Kuala Lumpur",
        "station_code": "WMKK",
        "station_name": "Kuala Lumpur Intl Airport Station",
        "timezone": "Asia/Kuala_Lumpur",
        "base_url": "https://www.wunderground.com/history/daily/my/sepang-district/WMKK",
        "anchor_date": date(2026, 6, 22),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def request_key(station: dict, requested_date: date) -> str:
    return f"{station['station_code']}-{requested_date.isoformat()}"


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.raw_dir.exists():
        raise FileExistsError("output and raw directory must be new immutable paths")
    requests = []
    for station in STATIONS:
        for offset in OFFSETS:
            requested_date = station["anchor_date"] - timedelta(days=offset)
            requests.append(
                (
                    station,
                    requested_date,
                    daily_url(station["base_url"], requested_date.isoformat()),
                )
            )

    fetched = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_daily_page, url): (station, requested_date)
            for station, requested_date, url in requests
        }
        for future in as_completed(futures):
            station, requested_date = futures[future]
            fetched[request_key(station, requested_date)] = future.result()

    args.raw_dir.mkdir(parents=True)
    records = []
    for station, requested_date, _ in requests:
        key = request_key(station, requested_date)
        retrieval = fetched[key]
        raw = retrieval.pop("raw")
        parsed = parse_daily_page(raw.decode("utf-8", errors="replace")) if raw else None
        repeated = parse_daily_page(raw.decode("utf-8", errors="replace")) if raw else None
        if raw:
            (args.raw_dir / f"{key}.html").write_bytes(raw)
        expected_page_date = f"{requested_date.year}-{requested_date.month}-{requested_date.day}"
        checks = {
            "http_200": retrieval["http_status"] == 200,
            "station_code_match": parsed is not None
            and parsed["station_code"] == station["station_code"],
            "station_name_match": parsed is not None
            and parsed["station_name"] == station["station_name"],
            "timezone_match": parsed is not None and parsed["timezone"] == station["timezone"],
            "requested_date_match": parsed is not None
            and parsed["page_date"] == expected_page_date,
            "daily_high_present": parsed is not None and parsed["daily_high"] is not None,
            "celsius_unit": parsed is not None and parsed["temperature_unit"] == "C",
            "observations_present": parsed is not None and parsed["observation_count"] > 0,
            "normalized_repeatable": parsed == repeated,
        }
        records.append(
            {
                "key": key,
                "city": station["city"],
                "station_code": station["station_code"],
                "requested_date": requested_date.isoformat(),
                "retrieval": retrieval,
                "parsed": parsed,
                "checks": checks,
                "complete": all(checks.values()),
            }
        )

    required_checks = tuple(records[0]["checks"])
    summary = {
        "expected_page_count": len(records),
        "complete_page_count": sum(record["complete"] for record in records),
        "coverage": sum(record["complete"] for record in records) / len(records),
        "terminal_transport_failure_count": sum(
            record["retrieval"]["http_status"] is None for record in records
        ),
        "check_pass_counts": {
            check: sum(record["checks"][check] for record in records)
            for check in required_checks
        },
    }
    summary["spike_gate_passed"] = (
        summary["complete_page_count"] == summary["expected_page_count"]
        and summary["terminal_transport_failure_count"] == 0
    )
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "wunderground-observation-retention-spike",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pre_registered_offsets_days": list(OFFSETS),
        "evidence_class": "CURRENT_OR_FINAL_HISTORICAL_PAGE_NOT_AS_OF_MARKET_FREEZE",
        "revision_limitation": (
            "Current retrieval cannot prove the value visible at the market's next-day freeze time."
        ),
        "summary": summary,
        "records": records,
    }
    (args.raw_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at_utc": artifact["generated_at_utc"],
                "records": [
                    {
                        "key": record["key"],
                        "url": record["retrieval"]["url"],
                        "sha256": record["retrieval"].get("sha256"),
                        "byte_count": record["retrieval"].get("byte_count"),
                    }
                    for record in records
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **summary}, indent=2))


if __name__ == "__main__":
    main()
