#!/usr/bin/env python3
"""Probe multi-station NBM probabilistic MaxT content on locked dates."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import (
    download_public_object,
    extract_station_block,
    parse_station_maxt,
    publication_is_admissible,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_date(run_date: str) -> str:
    return (
        datetime.strptime(run_date, "%Y%m%d").date() + timedelta(days=1)
    ).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    inventory_path = Path(config["source_nbm_inventory"])
    inventory = json.loads(inventory_path.read_text())
    targets = set(config["probe"]["target_dates"])
    selected = [row for row in inventory["records"] if target_date(row["run_date"]) in targets]
    if len(selected) != len(targets):
        raise ValueError("locked target dates do not map one-to-one to inventory")
    args.output.mkdir(parents=True)
    full_dir = args.output / "full_objects"
    full_dir.mkdir()
    retrievals = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for record in selected:
            source = record["attempts"][0]
            destination = full_dir / f"blend_nbptx.{record['run_date']}.t07z"
            futures[executor.submit(download_public_object, source["url"], destination, 90)] = (
                record,
                destination,
            )
        for future in as_completed(futures):
            record, destination = futures[future]
            retrievals.append(
                {
                    "record": record,
                    "destination": str(destination),
                    "retrieval": future.result(),
                }
            )
    retrievals.sort(key=lambda row: row["record"]["run_date"])
    required = tuple(config["probe"]["required_fields"])
    rows = []
    for item in retrievals:
        record, retrieval = item["record"], item["retrieval"]
        decision = datetime.strptime(record["run_date"], "%Y%m%d").replace(
            hour=11, tzinfo=timezone.utc
        )
        admissible = publication_is_admissible(
            retrieval["http_last_modified"], decision.isoformat()
        )
        full_path = Path(item["destination"])
        for station in config["us_cohort"]["stations"]:
            destination = args.output / "stations" / record["run_date"] / f"{station}.nbptx"
            error = None
            feature = None
            try:
                block = extract_station_block(full_path.read_bytes(), station)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(block)
                run_time = datetime.strptime(record["run_date"], "%Y%m%d").replace(
                    hour=config["probe"]["cycle_utc"], tzinfo=timezone.utc
                )
                parsed = parse_station_maxt(destination, station, run_time.isoformat())
                matches = [
                    row
                    for row in parsed["records"]
                    if row["forecast_hour"] == config["probe"]["forecast_hour"]
                ]
                if len(matches) != 1:
                    raise ValueError("expected exactly one locked forecast-hour record")
                feature = matches[0]
                if any(feature[field] is None for field in required):
                    raise ValueError("required field is missing")
            except (UnicodeDecodeError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
            rows.append(
                {
                    "run_date": record["run_date"],
                    "target_date": target_date(record["run_date"]),
                    "station_code": station,
                    "publication_admissible": admissible,
                    "source_last_modified": retrieval["http_last_modified"],
                    "station_block_path": str(destination) if destination.exists() else None,
                    "station_block_sha256": sha256(destination) if destination.exists() else None,
                    "feature": feature,
                    "error": error,
                    "passed": admissible and error is None,
                }
            )
    expected = len(config["us_cohort"]["stations"]) * len(targets)
    passed = [row for row in rows if row["passed"]]
    duplicate_count = len(rows) - len({(row["station_code"], row["target_date"]) for row in rows})
    leakage = sum(not row["publication_admissible"] for row in rows)
    summary = {
        "station_regime_count": len({row["station_code"] for row in rows}),
        "probe_date_count": len({row["target_date"] for row in rows}),
        "expected_station_date_count": expected,
        "passed_station_date_count": len(passed),
        "station_date_block_coverage": len(passed) / expected,
        "required_field_coverage": len(passed) / expected,
        "duplicate_station_date_count": duplicate_count,
        "temporal_leakage_count": leakage,
        "full_object_transfer_bytes": sum(row["retrieval"]["byte_count"] for row in retrievals),
        "error_count": sum(row["error"] is not None for row in rows),
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_station_regime_count": summary["station_regime_count"]
        == gates["exact_station_regime_count"],
        "exact_probe_date_count": summary["probe_date_count"] == gates["exact_probe_date_count"],
        "minimum_station_date_block_coverage": summary["station_date_block_coverage"]
        >= gates["minimum_station_date_block_coverage"],
        "minimum_required_field_coverage": summary["required_field_coverage"]
        >= gates["minimum_required_field_coverage"],
        "maximum_duplicate_station_date_count": duplicate_count
        <= gates["maximum_duplicate_station_date_count"],
        "maximum_temporal_leakage_count": leakage <= gates["maximum_temporal_leakage_count"],
    }
    (args.output / "station-dates.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_inventory_sha256": sha256(inventory_path),
        "summary": summary,
        "checks": checks,
        "decision": (
            "US_NBM_STATION_COVERAGE_PASS"
            if all(checks.values())
            else "US_NBM_STATION_COVERAGE_FAIL"
        ),
        "retrievals": retrievals,
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console = {key: value for key, value in result.items() if key != "retrievals"}
    print(json.dumps(console, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
