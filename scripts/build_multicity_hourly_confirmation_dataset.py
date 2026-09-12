#!/usr/bin/env python3
"""Download and quality-gate the preregistered multi-city NOAA LCDv2 cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path
from weather_quant.ingestion.noaa_lcdv2 import parse_lcdv2_hourly, parse_lcdv2_sod


def station_quality(
    hourly: list[dict], labels: list[dict], station_id: str, target_dates: list[date]
) -> dict:
    target_set = {value.isoformat() for value in target_dates}
    input_set = {(value - timedelta(days=1)).isoformat() for value in target_dates}
    admitted_hourly = [row for row in hourly if row["date_local_standard"] in input_set]
    admitted_labels = [row for row in labels if row["date"] in target_set]
    label_counts = Counter(row["date"] for row in admitted_labels)
    cutoff_temp_hours: dict[str, set[int]] = defaultdict(set)
    for row in admitted_hourly:
        if row["dry_bulb_c"] is not None and row["hour_local_standard"] <= 18:
            cutoff_temp_hours[row["date_local_standard"]].add(row["hour_local_standard"])
    labeled_dates = {
        row["date"]
        for row in admitted_labels
        if row["daily_maximum_dry_bulb_c"] is not None
    }
    station_rows = admitted_hourly + admitted_labels
    summary = {
        "target_day_count": len(target_dates),
        "hourly_row_count": len(admitted_hourly),
        "label_row_count": len(admitted_labels),
        "non_null_label_count": len(labeled_dates),
        "label_coverage": len(labeled_dates) / len(target_dates),
        "days_with_18_temperature_hours_through_cutoff": sum(
            len(cutoff_temp_hours[input_date]) >= 18 for input_date in input_set
        ),
        "days_with_18_temperature_hours_through_cutoff_rate": sum(
            len(cutoff_temp_hours[input_date]) >= 18 for input_date in input_set
        )
        / len(target_dates),
        "station_identity_error_count": sum(
            row["station"] != station_id for row in station_rows
        ),
        "unique_station_names": sorted({row["name"] for row in station_rows}),
        "duplicate_sod_date_count": sum(count > 1 for count in label_counts.values()),
        "out_of_range_temperature_count": sum(
            row["dry_bulb_c"] is not None and not -60 <= row["dry_bulb_c"] <= 60
            for row in admitted_hourly
        ),
        "first_hourly_timestamp": min(
            (row["timestamp_local_standard"] for row in admitted_hourly), default=None
        ),
        "last_hourly_timestamp": max(
            (row["timestamp_local_standard"] for row in admitted_hourly), default=None
        ),
    }
    return {"hourly": admitted_hourly, "labels": admitted_labels, "summary": summary}


def quality_checks(summary: dict, gates: dict, exact_days: int) -> dict[str, bool]:
    return {
        "exact_target_day_count": summary["target_day_count"] == exact_days,
        "minimum_label_coverage": summary["label_coverage"]
        >= gates["minimum_label_coverage"],
        "minimum_days_with_18_temperature_hours_through_cutoff_rate": summary[
            "days_with_18_temperature_hours_through_cutoff_rate"
        ]
        >= gates["minimum_days_with_18_temperature_hours_through_cutoff_rate"],
        "maximum_station_identity_error_count": summary["station_identity_error_count"]
        <= gates["maximum_station_identity_error_count"],
        "maximum_duplicate_sod_date_count": summary["duplicate_sod_date_count"]
        <= gates["maximum_duplicate_sod_date_count"],
        "maximum_out_of_range_temperature_count": summary[
            "out_of_range_temperature_count"
        ]
        <= gates["maximum_out_of_range_temperature_count"],
        "single_station_name": len(summary["unique_station_names"]) == 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.raw_output.exists() or args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    start = date.fromisoformat(config["window"]["start_date"])
    end = date.fromisoformat(config["window"]["end_date"])
    target_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    if len(target_dates) != config["window"]["exact_days_per_station"]:
        raise ValueError("configured window does not match exact_days_per_station")
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    args.raw_output.mkdir(parents=True)
    objects = []
    station_results = {}
    for station in config["stations"]:
        all_hourly = []
        all_labels = []
        for year in config["source"]["years"]:
            filename = f"LCD_{station['ghcn_id']}_{year}.csv"
            url = f"{config['source']['base_url']}/{year}/{filename}"
            request = urllib.request.Request(
                url, headers={"User-Agent": "weather-quant-research/0.1"}
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                content = response.read()
                headers = {
                    "etag": response.headers.get("ETag", "").strip(),
                    "last_modified": response.headers.get("Last-Modified", ""),
                }
            raw_path = args.raw_output / filename
            raw_path.write_bytes(content)
            all_hourly.extend(parse_lcdv2_hourly(content))
            all_labels.extend(parse_lcdv2_sod(content))
            objects.append(
                {
                    "station": station["icao"],
                    "url": url,
                    "filename": filename,
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "headers": headers,
                    "retrieved_at_utc": retrieved,
                }
            )
        quality = station_quality(all_hourly, all_labels, station["ghcn_id"], target_dates)
        checks = quality_checks(
            quality["summary"],
            config["data_quality_gates_per_station"],
            config["window"]["exact_days_per_station"],
        )
        station_dir = args.output / "stations" / station["icao"]
        station_dir.mkdir(parents=True)
        hourly_path = station_dir / "hourly.jsonl"
        labels_path = station_dir / "labels.jsonl"
        hourly_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in quality["hourly"])
        )
        labels_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in quality["labels"])
        )
        station_results[station["icao"]] = {
            "station": station,
            "summary": quality["summary"],
            "checks": checks,
            "artifacts": {
                "hourly": str(hourly_path),
                "hourly_sha256": sha256_path(hourly_path),
                "labels": str(labels_path),
                "labels_sha256": sha256_path(labels_path),
            },
            "passed": all(checks.values()),
        }
    passed = all(result["passed"] for result in station_results.values())
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": retrieved,
        "config_sha256": sha256_path(args.config),
        "objects": objects,
        "stations": station_results,
        "decision": "MULTICITY_DATA_QUALITY_PASS" if passed else "MULTICITY_DATA_QUALITY_FAIL",
        "boundary": {
            **config["boundary"],
            "model_not_scored": True,
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "stations": {
                    name: {
                        "summary": values["summary"],
                        "checks": values["checks"],
                        "passed": values["passed"],
                    }
                    for name, values in station_results.items()
                },
                "decision": result["decision"],
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
