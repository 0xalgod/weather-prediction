#!/usr/bin/env python3
"""Apply the preregistered sparse-invalid-value correction to multi-city data."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from scripts.build_multicity_hourly_confirmation_dataset import station_quality
from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.run_kord_hourly_nextday_model import read_jsonl


def correct_hourly_rows(rows: list[dict]) -> tuple[list[dict], int]:
    corrected = []
    correction_count = 0
    for source_row in rows:
        row = dict(source_row)
        temperature = row["dry_bulb_c"]
        if temperature is not None and not -60 <= temperature <= 60:
            row["original_dry_bulb_c"] = temperature
            row["original_relative_humidity_pct"] = row["relative_humidity_pct"]
            row["dry_bulb_c"] = None
            row["relative_humidity_pct"] = None
            row["quality_flags"] = [
                "OUT_OF_RANGE_DRY_BULB_NULLED",
                "DEPENDENT_RH_NULLED",
            ]
            correction_count += 1
        corrected.append(row)
    return corrected, correction_count


def correction_checks(summary: dict, gates: dict) -> dict[str, bool]:
    return {
        "maximum_corrected_hourly_row_fraction_per_station": summary[
            "corrected_hourly_row_fraction"
        ]
        <= gates["maximum_corrected_hourly_row_fraction_per_station"],
        "minimum_label_coverage": summary["label_coverage"]
        >= gates["minimum_label_coverage"],
        "minimum_days_with_18_temperature_hours_through_cutoff_rate": summary[
            "days_with_18_temperature_hours_through_cutoff_rate"
        ]
        >= gates["minimum_days_with_18_temperature_hours_through_cutoff_rate"],
        "maximum_remaining_out_of_range_temperature_count": summary[
            "out_of_range_temperature_count"
        ]
        <= gates["maximum_remaining_out_of_range_temperature_count"],
        "maximum_station_identity_error_count": summary["station_identity_error_count"]
        <= gates["maximum_station_identity_error_count"],
        "maximum_duplicate_sod_date_count": summary["duplicate_sod_date_count"]
        <= gates["maximum_duplicate_sod_date_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_result_path = Path(config["source_dataset_result"])
    confirmation_config_path = Path(config["source_confirmation_config"])
    if sha256_path(source_result_path) != config["source_dataset_result_sha256"]:
        raise ValueError("source dataset result checksum mismatch")
    if sha256_path(confirmation_config_path) != config["source_confirmation_config_sha256"]:
        raise ValueError("source confirmation config checksum mismatch")
    source_result = json.loads(source_result_path.read_text())
    confirmation = json.loads(confirmation_config_path.read_text())
    start = date.fromisoformat(confirmation["window"]["start_date"])
    end = date.fromisoformat(confirmation["window"]["end_date"])
    target_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    station_by_icao = {row["icao"]: row for row in confirmation["stations"]}
    station_results = {}
    for icao, source_station in source_result["stations"].items():
        hourly_path = Path(source_station["artifacts"]["hourly"])
        labels_path = Path(source_station["artifacts"]["labels"])
        if sha256_path(hourly_path) != source_station["artifacts"]["hourly_sha256"]:
            raise ValueError(f"hourly checksum mismatch: {icao}")
        if sha256_path(labels_path) != source_station["artifacts"]["labels_sha256"]:
            raise ValueError(f"labels checksum mismatch: {icao}")
        source_hourly = read_jsonl(hourly_path)
        labels = read_jsonl(labels_path)
        corrected_hourly, corrected_count = correct_hourly_rows(source_hourly)
        station = station_by_icao[icao]
        quality = station_quality(corrected_hourly, labels, station["ghcn_id"], target_dates)
        summary = quality["summary"]
        summary["corrected_hourly_row_count"] = corrected_count
        summary["corrected_hourly_row_fraction"] = corrected_count / len(source_hourly)
        checks = correction_checks(summary, config["acceptance_gates"])
        station_dir = args.output / "stations" / icao
        station_dir.mkdir(parents=True)
        corrected_hourly_path = station_dir / "hourly.jsonl"
        copied_labels_path = station_dir / "labels.jsonl"
        corrected_hourly_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in quality["hourly"])
        )
        copied_labels_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in quality["labels"])
        )
        station_results[icao] = {
            "station": station,
            "summary": summary,
            "checks": checks,
            "passed": all(checks.values()),
            "artifacts": {
                "hourly": str(corrected_hourly_path),
                "hourly_sha256": sha256_path(corrected_hourly_path),
                "labels": str(copied_labels_path),
                "labels_sha256": sha256_path(copied_labels_path),
            },
        }
    passed = all(row["passed"] for row in station_results.values())
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "source_dataset_result_sha256": sha256_path(source_result_path),
        "stations": station_results,
        "decision": "CORRECTED_DATASET_PASS" if passed else "CORRECTED_DATASET_FAIL",
        "boundary": config["boundary"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "stations": {
                    icao: {
                        "summary": row["summary"],
                        "checks": row["checks"],
                        "passed": row["passed"],
                    }
                    for icao, row in station_results.items()
                },
                "decision": result["decision"],
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
