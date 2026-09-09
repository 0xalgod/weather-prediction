#!/usr/bin/env python3
"""Probe publication timing and station content for prior-day 13Z NBM f35."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from weather_quant.ingestion.noaa_nbm import (
    download_public_object,
    extract_canonical_station_block,
    parse_station_maxt,
    probabilistic_text_url,
    publication_is_admissible,
)


def run_date(target_date: str) -> str:
    return (datetime.fromisoformat(target_date).date() - timedelta(days=1)).strftime("%Y%m%d")


def retrieve(target: str, destination: Path, config: dict) -> dict:
    run = run_date(target)
    url = probabilistic_text_url(run, config["probe"]["cycle_utc"])
    errors = []
    for attempt in range(1, config["transport"]["maximum_attempts"] + 1):
        try:
            return {
                "target_date": target,
                "run_date": run,
                "retrieval": download_public_object(
                    url, destination, config["transport"]["timeout_seconds"]
                ),
                "errors": errors,
            }
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            if destination.exists():
                destination.unlink()
            errors.append({"attempt": attempt, "error": f"{type(exc).__name__}: {exc}"})
            if attempt < config["transport"]["maximum_attempts"]:
                time.sleep(config["transport"]["retry_backoff_seconds"] * attempt)
    return {"target_date": target, "run_date": run, "retrieval": None, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    args.output.mkdir(parents=True)
    full_dir = args.output / "full_objects"
    full_dir.mkdir()
    retrievals = []
    with ThreadPoolExecutor(max_workers=config["transport"]["workers"]) as executor:
        futures = {
            executor.submit(
                retrieve,
                target,
                full_dir / f"blend_nbptx.{run_date(target)}.t13z",
                config,
            ): target
            for target in config["probe"]["target_dates"]
        }
        for future in as_completed(futures):
            retrievals.append(future.result())
    retrievals.sort(key=lambda row: row["target_date"])

    rows = []
    required = config["probe"]["required_fields"]
    conflict_count = 0
    for item in retrievals:
        retrieval = item["retrieval"]
        cutoff = datetime.strptime(item["run_date"], "%Y%m%d").replace(
            hour=18, tzinfo=timezone.utc
        )
        if retrieval is None:
            for station in config["probe"]["stations"]:
                rows.append(
                    {
                        "target_date": item["target_date"],
                        "station_code": station,
                        "passed": False,
                        "error": "FULL_OBJECT_RETRIEVAL_FAILED",
                    }
                )
            continue
        admissible = publication_is_admissible(
            retrieval["http_last_modified"], cutoff.isoformat()
        )
        content = Path(retrieval["local_path"]).read_bytes()
        for station in config["probe"]["stations"]:
            feature = None
            diagnostic = None
            error = None
            try:
                block, diagnostic = extract_canonical_station_block(content, station)
                station_path = args.output / "stations" / item["run_date"] / f"{station}.nbptx"
                station_path.parent.mkdir(parents=True, exist_ok=True)
                station_path.write_bytes(block)
                model_run = datetime.strptime(item["run_date"], "%Y%m%d").replace(
                    hour=config["probe"]["cycle_utc"], tzinfo=timezone.utc
                )
                parsed = parse_station_maxt(station_path, station, model_run.isoformat())
                matches = [
                    record
                    for record in parsed["records"]
                    if record["forecast_hour"] == config["probe"]["forecast_hour"]
                ]
                if len(matches) != 1:
                    raise ValueError("expected exactly one f35 feature")
                feature = matches[0]
                if any(feature[field] is None for field in required):
                    raise ValueError("required field missing")
            except (UnicodeDecodeError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                conflict_count += "conflicting duplicate" in str(exc)
            rows.append(
                {
                    "target_date": item["target_date"],
                    "run_date": item["run_date"],
                    "station_code": station,
                    "publication_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
                    "source_last_modified": retrieval["http_last_modified"],
                    "publication_admissible": admissible,
                    "canonicalization": diagnostic,
                    "feature": feature,
                    "passed": admissible and error is None,
                    "error": error,
                }
            )

    expected = len(config["probe"]["target_dates"]) * len(config["probe"]["stations"])
    passed = [row for row in rows if row["passed"]]
    transfer = sum(
        item["retrieval"]["byte_count"]
        for item in retrievals
        if item["retrieval"] is not None
    )
    summary = {
        "target_date_count": len(config["probe"]["target_dates"]),
        "station_count": len(config["probe"]["stations"]),
        "expected_station_date_count": expected,
        "passed_station_date_count": len(passed),
        "station_date_feature_rate": len(passed) / expected,
        "publication_after_cutoff_count": sum(
            row.get("publication_admissible") is False for row in rows
        ),
        "conflicting_duplicate_count": conflict_count,
        "full_object_transfer_bytes": transfer,
        "retrieval_failure_count": sum(item["retrieval"] is None for item in retrievals),
        "station_error_count": sum(row["error"] is not None for row in rows),
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_target_date_count": summary["target_date_count"] == gates["exact_target_date_count"],
        "exact_station_count": summary["station_count"] == gates["exact_station_count"],
        "minimum_station_date_feature_rate": summary["station_date_feature_rate"]
        >= gates["minimum_station_date_feature_rate"],
        "maximum_publication_after_cutoff_count": summary["publication_after_cutoff_count"]
        <= gates["maximum_publication_after_cutoff_count"],
        "maximum_conflicting_duplicate_count": conflict_count
        <= gates["maximum_conflicting_duplicate_count"],
        "maximum_transfer_bytes": transfer <= gates["maximum_transfer_bytes"],
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "summary": summary,
        "checks": checks,
        "decision": "NBM_13Z_COVERAGE_PASS" if all(checks.values()) else "NBM_13Z_COVERAGE_FAIL",
        "retrievals": retrievals,
        "boundary": config["boundary"],
    }
    (args.output / "station-dates.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console = {key: value for key, value in result.items() if key != "retrievals"}
    print(json.dumps(console, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
