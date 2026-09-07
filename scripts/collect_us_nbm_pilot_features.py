#!/usr/bin/env python3
"""Download frozen-date NBM objects and extract all US pilot station features."""

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
    publication_is_admissible,
)


def run_date_for_target(target_date: str) -> str:
    return (datetime.fromisoformat(target_date).date() - timedelta(days=1)).strftime("%Y%m%d")


def retrieve_with_retry(record: dict, destination: Path, settings: dict) -> dict:
    errors = []
    for attempt in range(1, settings["maximum_attempts"] + 1):
        try:
            retrieval = download_public_object(
                record["attempts"][0]["url"],
                destination,
                settings["request_timeout_seconds"],
            )
            return {"record": record, "retrieval": retrieval, "errors": errors}
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            if destination.exists():
                destination.unlink()
            errors.append({"attempt": attempt, "error": f"{type(exc).__name__}: {exc}"})
            if attempt < settings["maximum_attempts"]:
                time.sleep(settings["retry_backoff_seconds"] * attempt)
    return {"record": record, "retrieval": None, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    selection_path = args.selection / "result.json"
    selection = json.loads(selection_path.read_text())
    inventory_path = Path(config["source_nbm_inventory"])
    inventory = json.loads(inventory_path.read_text())
    inventory_by_date = {record["run_date"]: record for record in inventory["records"]}
    run_dates = [run_date_for_target(target) for target in selection["selected_dates"]]
    records = [inventory_by_date[run_date] for run_date in run_dates]
    stations = [
        "KATL", "KAUS", "KBKF", "KDEN", "KORD", "KDAL",
        "KHOU", "KLAX", "KMIA", "KLGA", "KSFO", "KSEA",
    ]
    settings = config["nbm_retrieval"]

    args.output.mkdir(parents=True)
    full_dir = args.output / "full_objects"
    full_dir.mkdir()
    retrievals = []
    with ThreadPoolExecutor(max_workers=settings["worker_count"]) as executor:
        futures = {
            executor.submit(
                retrieve_with_retry,
                record,
                full_dir / f"blend_nbptx.{record['run_date']}.t07z",
                settings,
            ): record
            for record in records
        }
        for future in as_completed(futures):
            retrievals.append(future.result())
    retrievals.sort(key=lambda row: row["record"]["run_date"])

    rows = []
    required = config["join_contract"]["required_nbm_fields"]
    for item in retrievals:
        run_date = item["record"]["run_date"]
        target_date = (datetime.strptime(run_date, "%Y%m%d").date() + timedelta(days=1)).isoformat()
        retrieval = item["retrieval"]
        if retrieval is None:
            for station in stations:
                rows.append(
                    {
                        "run_date": run_date,
                        "target_date": target_date,
                        "station_code": station,
                        "passed": False,
                        "error": "FULL_OBJECT_RETRIEVAL_FAILED",
                    }
                )
            continue
        decision = datetime.strptime(run_date, "%Y%m%d").replace(hour=11, tzinfo=timezone.utc)
        admissible = publication_is_admissible(
            retrieval["http_last_modified"], decision.isoformat()
        )
        content = Path(retrieval["local_path"]).read_bytes()
        for station in stations:
            destination = args.output / "stations" / run_date / f"{station}.nbptx"
            feature = None
            diagnostic = None
            error = None
            try:
                block, diagnostic = extract_canonical_station_block(content, station)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(block)
                model_run = datetime.strptime(run_date, "%Y%m%d").replace(
                    hour=config["join_contract"]["forecast_cycle_utc"], tzinfo=timezone.utc
                )
                parsed = parse_station_maxt(destination, station, model_run.isoformat())
                matches = [
                    record
                    for record in parsed["records"]
                    if record["forecast_hour"] == config["join_contract"]["forecast_hour"]
                ]
                if len(matches) != 1:
                    raise ValueError("expected exactly one f41 feature")
                feature = matches[0]
                if any(feature[field] is None for field in required):
                    raise ValueError("required NBM field missing")
            except (UnicodeDecodeError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
            rows.append(
                {
                    "run_date": run_date,
                    "target_date": target_date,
                    "station_code": station,
                    "publication_admissible": admissible,
                    "source_last_modified": retrieval["http_last_modified"],
                    "canonicalization": diagnostic,
                    "feature": feature,
                    "passed": admissible and error is None,
                    "error": error,
                }
            )

    expected = len(run_dates) * len(stations)
    passed = [row for row in rows if row["passed"]]
    transfer = sum(
        item["retrieval"]["byte_count"]
        for item in retrievals
        if item["retrieval"] is not None
    )
    summary = {
        "target_date_count": len(run_dates),
        "station_count": len(stations),
        "expected_station_date_count": expected,
        "passed_station_date_count": len(passed),
        "nbm_feature_rate": len(passed) / expected,
        "full_object_success_count": sum(item["retrieval"] is not None for item in retrievals),
        "full_object_failure_count": sum(item["retrieval"] is None for item in retrievals),
        "full_object_transfer_bytes": transfer,
        "temporal_leakage_count": sum(
            row.get("publication_admissible") is False for row in rows
        ),
        "station_error_count": sum(row["error"] is not None for row in rows),
        "identical_duplicate_set_count": sum(
            bool((row.get("canonicalization") or {}).get("identical_duplicate"))
            for row in rows
        ),
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "minimum_nbm_feature_rate": summary["nbm_feature_rate"]
        >= gates["minimum_nbm_feature_rate"],
        "maximum_temporal_leakage_count": summary["temporal_leakage_count"]
        <= gates["maximum_temporal_leakage_count"],
        "maximum_nbm_full_object_transfer_bytes": transfer
        <= gates["maximum_nbm_full_object_transfer_bytes"],
    }
    (args.output / "station-dates.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "stage": "nbm_feature_collection",
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "selection_result_sha256": sha256_path(selection_path),
        "source_nbm_inventory_sha256": sha256_path(inventory_path),
        "summary": summary,
        "checks": checks,
        "decision": (
            "NBM_FEATURE_COLLECTION_PASS"
            if all(checks.values())
            else "NBM_FEATURE_COLLECTION_FAIL"
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
