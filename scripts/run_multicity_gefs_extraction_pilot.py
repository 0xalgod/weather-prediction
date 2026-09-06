#!/usr/bin/env python3
"""Download and decode the preregistered global GEFS compact pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from weather_quant.features.multicity_gefs import longitude_stratified_sample
from weather_quant.ingestion.noaa_gefs import (
    aggregate_object_url,
    decode_nearest_tmax,
    download_selected_ranges,
    fetch_inventory,
    parse_max_window,
)
from weather_quant.ingestion.polymarket_price_history import parse_utc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retrieve(task: dict, output: Path, attempts: int) -> dict:
    url = aggregate_object_url(
        task["run_date"].replace("-", ""), 0, task["product"], task["step"]
    )
    destination = (
        output
        / "messages"
        / str(task["event_id"])
        / task["product"]
        / f"f{task['step']:03d}-tmax.grib2"
    )
    errors = []
    for attempt in range(1, attempts + 1):
        try:
            inventory = fetch_inventory(url, timeout=90)
            rows = [
                row
                for row in inventory["inventory"]["selected_rows"]
                if row["parameter"] == "TMAX" and row["level"] == "2 m above ground"
            ]
            if len(rows) != 1:
                raise ValueError("expected exactly one aggregate 2m TMAX row")
            start, end = parse_max_window(rows[0]["forecast_window"])
            if (start, end) != (task["step"] - 6, task["step"]):
                raise ValueError("non-canonical TMAX window")
            expected = "ens mean" if task["product"] == "geavg" else "ens std dev"
            if rows[0]["ensemble"] != expected:
                raise ValueError("aggregate ensemble semantic mismatch")
            published = datetime.strptime(
                inventory["http_last_modified"], "%a, %d %b %Y %H:%M:%S %Z"
            ).replace(tzinfo=timezone.utc)
            if published > parse_utc(task["cutoff_utc"]):
                raise ValueError("forecast object published after 18h cutoff")
            inventory["inventory"]["selected_rows"] = rows
            transfer = download_selected_ranges(inventory, destination, timeout=90)
            decoded = decode_nearest_tmax(
                destination, float(task["latitude"]), float(task["longitude"])
            )
            value_f = (
                decoded["temperature_f"]
                if task["product"] == "geavg"
                else decoded["temperature_k"] * 9 / 5
            )
            return {
                **task,
                "status": "SUCCESS",
                "value_f": value_f,
                "published_at_utc": published.isoformat(),
                "index_sha256": inventory["index_sha256"],
                "object_etag": inventory["http_etag"],
                "transfer": transfer,
                "decoded": decoded,
                "errors": errors,
            }
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            errors.append({"attempt": attempt, "kind": "TRANSPORT", "detail": str(exc)})
            if attempt < attempts:
                time.sleep(0.5 * attempt)
        except (ValueError, OSError) as exc:
            errors.append({"attempt": attempt, "kind": "CONTENT", "detail": str(exc)})
            break
    return {**task, "status": "FAILED", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    prices = [
        json.loads(line)
        for line in Path(config["source_price_horizons"]).read_text().splitlines()
    ]
    price_ids = {
        str(row["event_id"])
        for row in prices
        if row["horizon_hours"] == 18 and row["usable_full_vector"]
    }
    mapping = json.loads(Path(config["source_station_mapping"]).read_text())
    mapped = {
        str(row["event_id"]): row for row in mapping["rows"] if row["admitted"]
    }
    gefs_rows = [
        json.loads(line)
        for line in (Path(config["source_gefs_inventory"]) / "event-horizons.jsonl")
        .read_text()
        .splitlines()
    ]
    gefs = {
        str(row["event_id"]): row
        for row in gefs_rows
        if row["horizon_hours"] == 18 and row["complete_admissible"]
    }
    parent_ids = sorted(price_ids & set(mapped) & set(gefs))
    parent = [{**mapped[event_id], **gefs[event_id]} for event_id in parent_ids]
    pilot = longitude_stratified_sample(parent, config["cohort"]["pilot_event_count"])
    tasks = []
    for event in pilot:
        for step in [pair["step"] for pair in event["pairs"] if pair["product"] == "geavg"]:
            for product in config["forecast_contract"]["products"]:
                tasks.append(
                    {
                        "event_id": event["event_id"],
                        "city": event["city"],
                        "target_date": event["target_date"],
                        "station_code": event["station_code"],
                        "latitude": event["latitude"],
                        "longitude": event["longitude"],
                        "run_date": gefs[str(event["event_id"])]["target_date"],
                        "step": step,
                        "product": product,
                        "cutoff_utc": event["cutoff_utc"],
                    }
                )
    for task in tasks:
        task["run_date"] = (
            date.fromisoformat(task["target_date"]) - timedelta(days=1)
        ).isoformat()
    args.output.mkdir(parents=True)
    (args.output / "selected-events.json").write_text(
        json.dumps(pilot, indent=2, sort_keys=True) + "\n"
    )
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(retrieve, task, args.output, 3): task for task in tasks
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (row["event_id"], row["step"], row["product"]))
    success = [row for row in results if row["status"] == "SUCCESS"]
    thresholds = config["acceptance_thresholds"]
    physical = all(
        math.isfinite(row["value_f"])
        and (
            thresholds["mean_temperature_f_minimum"]
            <= row["value_f"]
            <= thresholds["mean_temperature_f_maximum"]
            if row["product"] == "geavg"
            else thresholds["spread_f_minimum"]
            <= row["value_f"]
            <= thresholds["spread_f_maximum"]
        )
        for row in success
    )
    transfer = sum(row["transfer"]["byte_count"] for row in success)
    parent_messages = sum(
        row["expected_pair_count"]
        for row in gefs.values()
        if str(row["event_id"]) in parent_ids
    )
    projected = transfer / len(tasks) * parent_messages if tasks else math.inf
    content_errors = sum(
        error["kind"] == "CONTENT" for row in results for error in row["errors"]
    )
    leakage = sum(
        row["status"] == "SUCCESS"
        and parse_utc(row["published_at_utc"]) > parse_utc(row["cutoff_utc"])
        for row in results
    )
    max_delta = max(
        (row["decoded"]["coordinate_delta_degrees"] for row in success), default=math.inf
    )
    summary = {
        "parent_event_count": len(parent),
        "parent_city_count": len({row["city"] for row in parent}),
        "selected_event_count": len(pilot),
        "selected_city_count": len({row["city"] for row in pilot}),
        "message_count": len(tasks),
        "message_success_count": len(success),
        "message_success_rate": len(success) / len(tasks),
        "content_error_count": content_errors,
        "temporal_leakage_count": leakage,
        "finite_plausible": physical,
        "maximum_coordinate_delta_degrees": max_delta,
        "observed_transfer_bytes": transfer,
        "parent_message_count": parent_messages,
        "projected_parent_transfer_bytes": projected,
    }
    checks = {
        "exact_selected_event_count": len(pilot) == thresholds["exact_selected_event_count"],
        "minimum_selected_city_count": summary["selected_city_count"]
        >= thresholds["minimum_selected_city_count"],
        "minimum_message_success_rate": summary["message_success_rate"]
        >= thresholds["minimum_message_success_rate"],
        "maximum_content_error_count": content_errors <= thresholds["maximum_content_error_count"],
        "maximum_coordinate_delta_degrees": max_delta
        <= thresholds["maximum_coordinate_delta_degrees"],
        "finite_plausible": physical,
        "maximum_projected_parent_transfer_bytes": projected
        <= thresholds["maximum_projected_parent_transfer_bytes"],
        "maximum_temporal_leakage_count": leakage
        <= thresholds["maximum_temporal_leakage_count"],
    }
    (args.output / "messages.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results)
    )
    decision_prefix = (
        "GEFS_FULL_INGESTION"
        if config["boundary"].get("full_forecast_ingestion_not_joined_dataset")
        else "GEFS_EXTRACTION_PILOT"
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "summary": summary,
        "checks": checks,
        "decision": f"{decision_prefix}_{'PASS' if all(checks.values()) else 'FAIL'}",
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
