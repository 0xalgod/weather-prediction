#!/usr/bin/env python3
"""Verify GEFS TMAX interval semantics against station-local calendar days."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_gefs import (
    download_selected_ranges,
    fetch_inventory,
    local_day_utc,
    object_url,
    parse_max_window,
    window_coverage,
)

CASES = (
    {
        "city": "Toronto",
        "station": "CYYZ",
        "timezone": "America/Toronto",
        "local_date": date(2026, 7, 23),
        "run_date": "20260722",
        "dst_expected": True,
    },
    {
        "city": "Kuala Lumpur",
        "station": "WMKK",
        "timezone": "Asia/Kuala_Lumpur",
        "local_date": date(2026, 6, 22),
        "run_date": "20260621",
        "dst_expected": False,
    },
)
STEPS = tuple(range(3, 55, 3))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"immutable artifact exists: {args.output}")
    case_results = []
    for case in CASES:
        run_time = datetime.strptime(case["run_date"], "%Y%m%d").replace(tzinfo=timezone.utc)
        inventories = {}
        actual_ranges = {}
        windows = []
        gate_a_rows = []
        for step in STEPS:
            inventory = fetch_inventory(object_url(case["run_date"], 0, "gec00", step))
            tmax_rows = [
                row
                for row in inventory["inventory"]["selected_rows"]
                if row["parameter"] == "TMAX"
            ]
            if len(tmax_rows) != 1:
                raise ValueError(f"expected one TMAX row at f{step:03d}")
            start_hour, end_hour = parse_max_window(tmax_rows[0]["forecast_window"])
            row = {
                "step": step,
                "forecast_window": tmax_rows[0]["forecast_window"],
                "start_hour": start_hour,
                "end_hour": end_hour,
                "matches_preregistered_three_hour_window": (start_hour, end_hour)
                == (step - 3, step),
            }
            gate_a_rows.append(row)
            windows.append(
                (run_time + timedelta(hours=start_hour), run_time + timedelta(hours=end_hour))
            )
            inventories[f"f{step:03d}"] = {
                key: inventory[key]
                for key in (
                    "url",
                    "requested_at_utc",
                    "received_at_utc",
                    "retrieval_seconds",
                    "http_status",
                    "index_http_status",
                    "object_byte_count",
                    "index_byte_count",
                    "index_sha256",
                    "http_last_modified",
                    "http_etag",
                    "index_http_last_modified",
                )
            } | {"tmax_row": tmax_rows[0]}

        target_start, target_end = local_day_utc(case["local_date"], case["timezone"])
        six_hour_pairs = [
            (row, window)
            for row, window in zip(gate_a_rows, windows)
            if row["step"] % 6 == 0
        ]
        six_hour_windows = [window for _, window in six_hour_pairs]
        coverage = window_coverage(target_start, target_end, six_hour_windows)
        overlapping_steps = [
            row["step"]
            for row, (start, end) in six_hour_pairs
            if start < target_end and end > target_start
        ]
        for step in overlapping_steps:
            full = fetch_inventory(object_url(case["run_date"], 0, "gec00", step))
            full["inventory"]["selected_rows"] = [
                row
                for row in full["inventory"]["selected_rows"]
                if row["parameter"] == "TMAX"
            ]
            destination = (
                args.raw_dir
                / case["run_date"]
                / f"gec00-f{step:03d}-tmax.grib2"
            )
            actual_ranges[f"f{step:03d}"] = download_selected_ranges(full, destination)

        six_hour_rows = [row for row, _ in six_hour_pairs]
        six_hour_consecutive = all(
            current["end_hour"] == following["start_hour"]
            for current, following in zip(six_hour_rows, six_hour_rows[1:])
        )
        case_results.append(
            {
                **case,
                "local_date": case["local_date"].isoformat(),
                "run_time_utc": iso(run_time),
                "local_day_start_utc": iso(target_start),
                "local_day_end_utc": iso(target_end),
                "local_day_duration_hours": (target_end - target_start).total_seconds() / 3600,
                "gate_a_all_three_hour_windows": all(
                    row["matches_preregistered_three_hour_window"] for row in gate_a_rows
                ),
                "observed_six_hour_series_consecutive": six_hour_consecutive,
                "window_rows": gate_a_rows,
                "overlapping_steps": overlapping_steps,
                "coverage": coverage,
                "actual_tmax_ranges": actual_ranges,
                "inventories": inventories,
            }
        )

    actual_range_passed = all(
        item["grib_message_count"] == 1
        and item["range_http_statuses"] == [206]
        and item["starts_with_grib"]
        and item["ends_with_7777"]
        for case in case_results
        for item in case["actual_tmax_ranges"].values()
    )
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "noaa-gefs-local-day-tmax-semantics",
        "schema_version": "1.0.0",
        "generated_at_utc": iso(datetime.now(timezone.utc)),
        "pre_registered_acceptance": {
            "gate_a": "each f003 step is an exact (step-3)-step three-hour TMAX window",
            "gate_b": "selected windows exactly partition each station-local day",
            "actual_range_integrity": "HTTP 206, one GRIB message, GRIB/7777 boundaries",
        },
        "cases": case_results,
        "checks": {
            "gate_a_passed": all(case["gate_a_all_three_hour_windows"] for case in case_results),
            "observed_six_hour_series_consecutive": all(
                case["observed_six_hour_series_consecutive"] for case in case_results
            ),
            "gate_b_passed": all(case["coverage"]["exact_partition"] for case in case_results),
            "actual_range_integrity_passed": actual_range_passed,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "checks": artifact["checks"]}, indent=2))


if __name__ == "__main__":
    main()
