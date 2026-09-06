#!/usr/bin/env python3
"""Inventory time-correct GEFS aggregate TMAX objects for mapped weather events."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from weather_quant.ingestion.noaa_gefs import (
    aggregate_object_url,
    list_run_prefix,
    local_day_tmax_steps,
)
from weather_quant.ingestion.polymarket_price_history import parse_utc
from weather_quant.normalization.station_verification import timezone_at_point


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retrieve_listing(run_date: str, settings: dict) -> dict:
    errors = []
    for attempt in range(1, int(settings["maximum_attempts"]) + 1):
        try:
            return {
                "run_date": run_date,
                "request_ok": True,
                "listing": list_run_prefix(
                    run_date.replace("-", ""),
                    cycle=0,
                    timeout=float(settings["request_timeout_seconds"]),
                ),
                "errors": errors,
            }
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            errors.append({"attempt": attempt, "kind": type(exc).__name__, "detail": str(exc)})
            if attempt < int(settings["maximum_attempts"]):
                time.sleep(0.5 * attempt)
    return {"run_date": run_date, "request_ok": False, "listing": None, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    mapping = json.loads(Path(config["source_station_mapping"]).read_text())
    selected = {
        str(row["event_id"]): row
        for row in json.loads(Path(config["source_selected_events"]).read_text())
    }
    with zipfile.ZipFile(config["timezone_boundaries"]) as archive:
        with archive.open(archive.namelist()[0]) as source:
            timezone_features = json.load(source)["features"]
    events = []
    timezone_failures = []
    for row in mapping["rows"]:
        if not row["admitted"]:
            continue
        event = selected[str(row["event_id"])]
        try:
            boundary_zone = timezone_at_point(
                float(row["longitude"]), float(row["latitude"]), timezone_features
            )
            timezone_name = boundary_zone
            semantics = local_day_tmax_steps(date.fromisoformat(row["target_date"]), timezone_name)
        except (KeyError, TypeError, ValueError) as exc:
            timezone_failures.append(
                {"event_id": row["event_id"], "error": f"{type(exc).__name__}: {exc}"}
            )
            continue
        events.append(
            {
                **row,
                "end_date_utc": event["end_date_utc"],
                "timezone_boundary": boundary_zone,
                "timezone": timezone_name,
                "semantics": semantics,
                "run_date": (
                    date.fromisoformat(row["target_date"]) - timedelta(days=1)
                ).isoformat(),
            }
        )

    run_dates = sorted({row["run_date"] for row in events})
    listings = {}
    with ThreadPoolExecutor(max_workers=int(config["retrieval"]["workers"])) as executor:
        futures = {
            executor.submit(retrieve_listing, run_date, config["retrieval"]): run_date
            for run_date in run_dates
        }
        for future in as_completed(futures):
            result = future.result()
            listings[result["run_date"]] = result

    horizon_rows = []
    products = config["forecast_contract"]["products"]
    for event in events:
        listing_result = listings[event["run_date"]]
        objects = (
            {item["key"]: item for item in listing_result["listing"]["objects"]}
            if listing_result["request_ok"]
            else {}
        )
        for horizon in config["forecast_contract"]["horizons_hours_before_end_date"]:
            cutoff = parse_utc(event["end_date_utc"]) - timedelta(hours=int(horizon))
            pairs = []
            for step in event["semantics"]["overlap_steps"]:
                for product in products:
                    url = aggregate_object_url(
                        event["run_date"].replace("-", ""), 0, product, int(step)
                    )
                    key = url.split(".com/", 1)[1]
                    data, index = objects.get(key), objects.get(key + ".idx")
                    timestamps = [
                        parse_utc(item["last_modified"])
                        for item in (data, index)
                        if item and item.get("last_modified")
                    ]
                    complete = data is not None and index is not None and len(timestamps) == 2
                    published = max(timestamps) if complete else None
                    pairs.append(
                        {
                            "product": product,
                            "step": step,
                            "complete": complete,
                            "published_at_utc": published.isoformat() if published else None,
                            "publication_admissible": bool(complete and published <= cutoff),
                        }
                    )
            horizon_rows.append(
                {
                    "event_id": event["event_id"],
                    "city": event["city"],
                    "station_code": event["station_code"],
                    "target_date": event["target_date"],
                    "horizon_hours": horizon,
                    "cutoff_utc": cutoff.isoformat(),
                    "timezone": event["timezone"],
                    "outside_local_seconds": event["semantics"]["outside_local_seconds"],
                    "exact_partition": event["semantics"]["exact_partition"],
                    "expected_pair_count": len(pairs),
                    "complete_pair_count": sum(pair["complete"] for pair in pairs),
                    "admissible_pair_count": sum(
                        pair["publication_admissible"] for pair in pairs
                    ),
                    "complete_admissible": all(
                        pair["publication_admissible"] for pair in pairs
                    ),
                    "pairs": pairs,
                }
            )

    by_horizon = {}
    for horizon in config["forecast_contract"]["horizons_hours_before_end_date"]:
        subset = [row for row in horizon_rows if row["horizon_hours"] == horizon]
        admitted = [row for row in subset if row["complete_admissible"]]
        by_horizon[str(horizon)] = {
            "event_count": len(subset),
            "complete_admissible_event_count": len(admitted),
            "complete_admissible_event_rate": len(admitted) / len(subset) if subset else 0.0,
            "complete_admissible_city_count": len({row["city"] for row in admitted}),
            "exact_partition_event_count": sum(row["exact_partition"] for row in subset),
            "proxy_partition_event_count": sum(not row["exact_partition"] for row in subset),
        }
    listing_errors = sum(not row["request_ok"] for row in listings.values())
    event_ids = [str(row["event_id"]) for row in events]
    summary = {
        "admitted_event_count": len(events),
        "admitted_city_count": len({row["city"] for row in events}),
        "duplicate_event_count": len(event_ids) - len(set(event_ids)),
        "timezone_resolution_failure_count": len(timezone_failures),
        "unique_run_date_count": len(run_dates),
        "listing_request_error_count": listing_errors,
        "listing_request_error_rate": listing_errors / len(run_dates) if run_dates else 0.0,
        "by_horizon": by_horizon,
    }
    primary = by_horizon["18"]
    thresholds = config["acceptance_thresholds"]
    checks = {
        "exact_admitted_event_count": summary["admitted_event_count"]
        == thresholds["exact_admitted_event_count"],
        "maximum_timezone_resolution_failure_count": len(timezone_failures)
        <= thresholds["maximum_timezone_resolution_failure_count"],
        "maximum_listing_request_error_rate": summary["listing_request_error_rate"]
        <= thresholds["maximum_listing_request_error_rate"],
        "minimum_complete_admissible_event_rate_at_18h": primary[
            "complete_admissible_event_rate"
        ]
        >= thresholds["minimum_complete_admissible_event_rate_at_18h"],
        "minimum_complete_admissible_city_count_at_18h": primary[
            "complete_admissible_city_count"
        ]
        >= thresholds["minimum_complete_admissible_city_count_at_18h"],
        "maximum_duplicate_event_count": summary["duplicate_event_count"]
        <= thresholds["maximum_duplicate_event_count"],
    }
    args.output.mkdir(parents=True)
    (args.output / "listings.json").write_text(
        json.dumps(listings, indent=2, sort_keys=True) + "\n"
    )
    (args.output / "event-horizons.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in horizon_rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "station_mapping_sha256": sha256(Path(config["source_station_mapping"])),
        "selected_events_sha256": sha256(Path(config["source_selected_events"])),
        "timezone_boundary_sha256": sha256(Path(config["timezone_boundaries"])),
        "timezone_aliases_sha256": sha256(Path(config["timezone_aliases"])),
        "summary": summary,
        "checks": checks,
        "decision": "GEFS_AVAILABILITY_PASS" if all(checks.values()) else "GEFS_AVAILABILITY_FAIL",
        "timezone_failures": timezone_failures,
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
