#!/usr/bin/env python3
"""Measure locked 365-day Wunderground current/final observation coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

from weather_quant.ingestion.wunderground import (
    daily_url,
    date_window_ending,
    fetch_daily_page,
    parse_daily_page,
)

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
DAYS = 365


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def compact_parse(parsed: dict) -> dict:
    observations = parsed.pop("observations")
    parsed["observations_sha256"] = hashlib.sha256(
        json.dumps(observations, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return parsed


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.raw_dir.exists():
        raise FileExistsError("output and raw directory must be new immutable paths")
    requests = [
        (station, requested_date, daily_url(station["base_url"], requested_date.isoformat()))
        for station in STATIONS
        for requested_date in date_window_ending(station["anchor_date"], DAYS)
    ]
    fetched = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_daily_page, url): (station, requested_date)
            for station, requested_date, url in requests
        }
        for future in as_completed(futures):
            station, requested_date = futures[future]
            fetched[(station["station_code"], requested_date.isoformat())] = future.result()

    args.raw_dir.mkdir(parents=True)
    records = []
    for station, requested_date, _ in requests:
        retrieval = fetched[(station["station_code"], requested_date.isoformat())]
        raw = retrieval.pop("raw")
        parsed = compact_parse(
            parse_daily_page(raw.decode("utf-8", errors="replace"))
        ) if raw else None
        if raw:
            filename = f"{station['station_code']}-{requested_date.isoformat()}.html"
            (args.raw_dir / filename).write_bytes(raw)
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
            "high_equals_observation_max": parsed is not None
            and parsed["daily_high"] == parsed["observation_temperature_max"],
        }
        records.append(
            {
                "city": station["city"],
                "station_code": station["station_code"],
                "requested_date": requested_date.isoformat(),
                "retrieval": retrieval,
                "parsed": parsed,
                "checks": checks,
                "complete": all(checks.values()),
            }
        )

    station_summaries = {}
    for station in STATIONS:
        station_records = [
            record for record in records if record["station_code"] == station["station_code"]
        ]
        complete = sum(record["complete"] for record in station_records)
        available = [record for record in station_records if record["checks"]["http_200"]]
        identity_checks = (
            "station_code_match",
            "station_name_match",
            "timezone_match",
            "requested_date_match",
        )
        station_summaries[station["station_code"]] = {
            "start_date": station_records[0]["requested_date"],
            "end_date": station_records[-1]["requested_date"],
            "expected_page_count": DAYS,
            "complete_page_count": complete,
            "coverage": complete / DAYS,
            "http_available_count": len(available),
            "identity_pass_counts_among_available": {
                check: sum(record["checks"][check] for record in available)
                for check in identity_checks
            },
            "high_observation_match_count": sum(
                record["checks"]["high_equals_observation_max"] for record in station_records
            ),
            "terminal_transport_failure_count": sum(
                record["retrieval"]["http_status"] is None for record in station_records
            ),
        }
    gate_passed = all(
        summary["coverage"] >= 0.99
        and summary["terminal_transport_failure_count"] == 0
        and all(
            count == summary["http_available_count"]
            for count in summary["identity_pass_counts_among_available"].values()
        )
        and summary["high_observation_match_count"] == DAYS
        for summary in station_summaries.values()
    )
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "wunderground-current-final-observation-coverage-365d",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evidence_class": "CURRENT_OR_FINAL_HISTORICAL_PAGE_NOT_AS_OF_MARKET_FREEZE",
        "pre_registered_acceptance": {
            "coverage_per_station_minimum": 0.99,
            "terminal_transport_failure_count": 0,
            "identity_rate_among_available": 1.0,
            "high_equals_observation_max_rate": 1.0,
        },
        "station_summaries": station_summaries,
        "gate_passed": gate_passed,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.raw_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at_utc": artifact["generated_at_utc"],
                "record_count": len(records),
                "records": [
                    {
                        "station_code": record["station_code"],
                        "requested_date": record["requested_date"],
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
    print(
        json.dumps(
            {"output": str(args.output), "gate_passed": gate_passed, **station_summaries},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
