#!/usr/bin/env python3
"""Measure operational NOAA GEFS member/field coverage and historical retention."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from weather_quant.ingestion.noaa_gefs import (
    REQUIRED_FIELDS,
    download_selected_ranges,
    fetch_inventory,
    member_names,
    object_url,
)

REPRESENTATIVE_MEMBERS = ("gec00", "gep01", "gep30")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dates", nargs="+", required=True, help="Current then historical YYYYMMDD"
    )
    parser.add_argument("--cycle", type=int, default=0)
    parser.add_argument("--step", type=int, default=24)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def availability_seconds(run_date: str, cycle: int, last_modified: str) -> float:
    run_time = datetime.strptime(f"{run_date}{cycle:02d}", "%Y%m%d%H").replace(
        tzinfo=timezone.utc
    )
    return (parsedate_to_datetime(last_modified) - run_time).total_seconds()


def main() -> None:
    args = parse_args()
    if len(args.dates) < 2:
        raise ValueError("at least current and historical dates are required")
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    runs = {}
    for run_date in args.dates:
        inventories = {}
        for member in member_names():
            inventory = fetch_inventory(
                object_url(run_date, args.cycle, member, args.step)
            )
            inventory["availability_seconds_after_run"] = availability_seconds(
                run_date, args.cycle, inventory["http_last_modified"]
            )
            inventories[member] = inventory

        actual_subsets = {}
        for member in REPRESENTATIVE_MEMBERS:
            destination = args.raw_dir / run_date / f"{member}-f{args.step:03d}-temp.grib2"
            actual_subsets[member] = download_selected_ranges(
                inventories[member], destination
            )

        complete = [
            member
            for member, item in inventories.items()
            if item["inventory"]["required_field_counts"]
            == {field: 1 for field in REQUIRED_FIELDS}
        ]
        runs[run_date] = {
            "run_time_utc": (
                f"{run_date[:4]}-{run_date[4:6]}-{run_date[6:]}"
                f"T{args.cycle:02d}:00:00Z"
            ),
            "member_count": len(inventories),
            "complete_member_count": len(complete),
            "complete_members": complete,
            "availability_seconds_min": min(
                item["availability_seconds_after_run"] for item in inventories.values()
            ),
            "availability_seconds_max": max(
                item["availability_seconds_after_run"] for item in inventories.values()
            ),
            "full_object_bytes_total": sum(
                item["object_byte_count"] for item in inventories.values()
            ),
            "selected_range_bytes_total": sum(
                item["inventory"]["selected_range_bytes"] for item in inventories.values()
            ),
            "inventories": inventories,
            "actual_subsets": actual_subsets,
        }

    parsed_dates = [datetime.strptime(value, "%Y%m%d").date() for value in args.dates]
    oldest_age_days = (max(parsed_dates) - min(parsed_dates)).days
    checks = {
        "all_dates_have_31_complete_members": all(
            run["member_count"] == 31 and run["complete_member_count"] == 31
            for run in runs.values()
        ),
        "representative_subsets_have_three_valid_messages": all(
            subset["grib_message_count"] == 3
            and subset["starts_with_grib"]
            and subset["ends_with_7777"]
            and subset["range_http_statuses"] == [206, 206, 206]
            for run in runs.values()
            for subset in run["actual_subsets"].values()
        ),
        "operational_retention_at_least_365_days": oldest_age_days >= 365,
        "oldest_observed_age_days": oldest_age_days,
    }
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "noaa-gefs-operational-archive",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "bucket": "noaa-gefs-pds",
            "product": "pgrb2sp25",
            "grid_degrees": 0.25,
            "reforecast_counts_as_operational_history": False,
        },
        "request": {"dates": args.dates, "cycle": args.cycle, "step": args.step},
        "pre_registered_acceptance": {
            "member_count_per_date": 31,
            "required_fields_per_member": {field: 1 for field in REQUIRED_FIELDS},
            "actual_subset_members": list(REPRESENTATIVE_MEMBERS),
            "actual_messages_per_subset": 3,
            "historical_retention_days_minimum": 365,
        },
        "runs": runs,
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
