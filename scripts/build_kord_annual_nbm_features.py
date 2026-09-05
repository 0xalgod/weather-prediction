#!/usr/bin/env python3
"""Build immutable compact KORD NBM features from a checksum-locked inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from weather_quant.ingestion.noaa_nbm import (
    download_station_range,
    parse_station_maxt,
    publication_is_admissible,
)

STATION = "KORD"
MODEL_CYCLE_UTC = 7
TARGET_FORECAST_HOUR = 41
CANDIDATE_RANGES = (
    (20_500_000, 21_500_000),
    (22_500_000, 23_500_000),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--inventory-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--attempts", type=int, default=3)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decision_time(run_date: str) -> datetime:
    return datetime.strptime(run_date, "%Y%m%d").replace(
        hour=11, tzinfo=timezone.utc
    )


def target_date(run_date: str) -> str:
    value = datetime.strptime(run_date, "%Y%m%d").date() + timedelta(days=1)
    return value.isoformat()


def select_admissible(records: list[dict]) -> tuple[list[dict], list[dict]]:
    admitted = []
    excluded = []
    for record in records:
        attempts = record["attempts"]
        if len(attempts) != 1 or attempts[0]["cycle_utc"] != MODEL_CYCLE_UTC:
            raise ValueError("inventory record violates locked 07Z-only policy")
        source = attempts[0]
        reason = None
        if source["http_status"] != 200:
            reason = "SOURCE_UNAVAILABLE"
        elif not publication_is_admissible(
            source["last_modified"],
            decision_time(record["run_date"]).isoformat(),
        ):
            reason = "PUBLISHED_AFTER_DECISION"
        if reason:
            excluded.append(
                {
                    "run_date": record["run_date"],
                    "target_date": target_date(record["run_date"]),
                    "reason": reason,
                }
            )
        else:
            admitted.append(record)
    return admitted, excluded


def retrieve_one(record: dict, output_dir: Path, attempts: int) -> dict:
    run_date = record["run_date"]
    source = record["attempts"][0]
    destination = output_dir / "stations" / f"KORD.{run_date}.t07z.nbptx"
    failures = []
    for byte_start, byte_end in CANDIDATE_RANGES:
        for attempt in range(1, attempts + 1):
            try:
                retrieval = download_station_range(
                    source["url"],
                    STATION,
                    byte_start,
                    byte_end,
                    destination,
                    timeout=90,
                )
                model_run = datetime.strptime(run_date, "%Y%m%d").replace(
                    hour=MODEL_CYCLE_UTC, tzinfo=timezone.utc
                )
                parsed = parse_station_maxt(
                    destination, STATION, model_run.isoformat()
                )
                targets = [
                    item
                    for item in parsed["records"]
                    if item["forecast_hour"] == TARGET_FORECAST_HOUR
                ]
                if len(targets) != 1:
                    raise ValueError("expected exactly one f41 record")
                required = (
                    "mean_f",
                    "standard_deviation_f",
                    "p10_f",
                    "p25_f",
                    "p50_f",
                    "p75_f",
                    "p90_f",
                )
                if any(targets[0][field] is None for field in required):
                    raise ValueError("f41 record has missing required values")
                return {
                    "run_date": run_date,
                    "target_date": target_date(run_date),
                    "status": "ADMITTED",
                    "source_last_modified": source["last_modified"],
                    "source_etag": source["etag"],
                    "retrieval": retrieval,
                    "nbm_version": parsed["nbm_version"],
                    "feature": targets[0],
                    "failed_attempts": failures,
                }
            except (HTTPError, URLError, TimeoutError, ConnectionError) as error:
                failures.append(
                    {
                        "range": [byte_start, byte_end],
                        "attempt": attempt,
                        "kind": "TRANSPORT",
                        "detail": str(error),
                    }
                )
                if attempt < attempts:
                    time.sleep(0.25 * attempt)
            except (UnicodeDecodeError, ValueError) as error:
                failures.append(
                    {
                        "range": [byte_start, byte_end],
                        "attempt": attempt,
                        "kind": "CONTENT",
                        "detail": str(error),
                    }
                )
                break
    return {
        "run_date": run_date,
        "target_date": target_date(run_date),
        "status": "FAILED",
        "failed_attempts": failures,
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError("batch output directory must be immutable")
    observed_sha = sha256_path(args.inventory)
    if observed_sha != args.inventory_sha256:
        raise ValueError("inventory checksum mismatch")
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    if inventory["date_count"] != 365 or inventory["primary_cycle_utc"] != 7:
        raise ValueError("inventory does not match locked 365-day 07Z contract")
    admitted, excluded = select_admissible(inventory["records"])
    if len(admitted) != 362 or len(excluded) != 3:
        raise ValueError("admissible/excluded inventory counts changed")
    args.output_dir.mkdir(parents=True)
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(retrieve_one, record, args.output_dir, args.attempts): record
            for record in admitted
        }
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda item: item["run_date"])
    success = [row for row in rows if row["status"] == "ADMITTED"]
    failed = [row for row in rows if row["status"] == "FAILED"]
    version_counts: dict[str, int] = {}
    for row in success:
        version = row["nbm_version"]
        version_counts[version] = version_counts.get(version, 0) + 1
    artifact = {
        "schema_version": "1.0.0",
        "experiment_id": "EXP-20260905-kord-forecast-dataset-v1",
        "substep": "annual_nbm_compact_features",
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "source_inventory": str(args.inventory),
        "source_inventory_sha256": observed_sha,
        "contract": {
            "station": STATION,
            "cycle_utc": MODEL_CYCLE_UTC,
            "target_forecast_hour": TARGET_FORECAST_HOUR,
            "candidate_ranges": [list(item) for item in CANDIDATE_RANGES],
            "expected_inventory_count": 365,
            "expected_publication_admissible_count": 362,
            "publication_leakage_maximum": 0,
        },
        "summary": {
            "inventory_count": len(inventory["records"]),
            "publication_admissible_count": len(admitted),
            "publication_excluded_count": len(excluded),
            "retrieval_success_count": len(success),
            "retrieval_failure_count": len(failed),
            "required_field_complete_rate": len(success) / len(admitted),
            "nbm_version_counts": dict(sorted(version_counts.items())),
            "passed": len(success) / len(admitted) >= 0.99,
        },
        "publication_exclusions": excluded,
        "rows": rows,
    }
    result_path = args.output_dir / "result.json"
    result_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    if not artifact["summary"]["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
