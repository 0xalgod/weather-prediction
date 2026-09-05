#!/usr/bin/env python3
"""Run the preregistered two-regime KORD GEFS extraction pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from weather_quant.ingestion.noaa_gefs import (
    decode_nearest_tmax,
    download_selected_ranges,
    fetch_inventory,
    member_names,
    object_url,
    parse_max_window,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--attempts", type=int, default=3)
    return parser.parse_args()


def retrieve_message(task: dict, output_dir: Path, station: dict, attempts: int) -> dict:
    url = object_url(task["run_date"].replace("-", ""), 0, task["member"], task["step"])
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
                raise ValueError("expected exactly one 2 m TMAX index row")
            start_hour, end_hour = parse_max_window(rows[0]["forecast_window"])
            if end_hour != task["step"] or start_hour != task["step"] - 6:
                raise ValueError("TMAX row is not the canonical six-hour window")
            published = datetime.strptime(
                inventory["http_last_modified"], "%a, %d %b %Y %H:%M:%S %Z"
            ).replace(tzinfo=timezone.utc)
            decision = datetime.fromisoformat(task["run_date"] + "T11:00:00+00:00")
            if published > decision:
                raise ValueError("object was published after decision time")
            inventory["inventory"]["selected_rows"] = rows
            destination = (
                output_dir
                / task["target_date"]
                / task["member"]
                / f"f{task['step']:03d}-tmax.grib2"
            )
            retrieval = download_selected_ranges(inventory, destination, timeout=90)
            decoded = decode_nearest_tmax(
                destination, station["latitude"], station["longitude"]
            )
            return {
                **task,
                "status": "SUCCESS",
                "index": {
                    "sha256": inventory["index_sha256"],
                    "byte_count": inventory["index_byte_count"],
                    "tmax_row": rows[0],
                },
                "object": {
                    "byte_count": inventory["object_byte_count"],
                    "etag": inventory["http_etag"],
                    "last_modified": inventory["http_last_modified"],
                },
                "retrieval": retrieval,
                "decoded": decoded,
                "errors": errors,
            }
        except (HTTPError, URLError, TimeoutError, ConnectionError) as error:
            errors.append(
                {"attempt": attempt, "kind": "TRANSPORT", "detail": str(error)}
            )
            if attempt < attempts:
                time.sleep(0.5 * attempt)
        except (ValueError, OSError) as error:
            errors.append(
                {"attempt": attempt, "kind": "CONTENT", "detail": str(error)}
            )
            break
    return {**task, "status": "FAILED", "errors": errors}


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError("pilot output directory must be immutable")
    config_raw = args.config.read_bytes()
    config = json.loads(config_raw)
    cases = config["cases"]
    expected = config["acceptance_thresholds"]["expected_message_count_exact"]
    tasks = [
        {
            "target_date": case["target_date"],
            "run_date": case["run_date"],
            "regime": case["regime"],
            "member": member,
            "step": step,
        }
        for case in cases
        for member in member_names()
        for step in case["expected_steps"]
    ]
    if len(tasks) != expected:
        raise ValueError("pilot task count does not match preregistration")
    args.output_dir.mkdir(parents=True)
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                retrieve_message,
                task,
                args.output_dir,
                config["station"],
                args.attempts,
            ): task
            for task in tasks
        }
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: (row["target_date"], row["member"], row["step"]))
    success = [row for row in rows if row["status"] == "SUCCESS"]
    failed = [row for row in rows if row["status"] == "FAILED"]
    total_bytes = sum(row["retrieval"]["byte_count"] for row in success)
    annual_pairs = config["annual_projection_basis"]["admissible_data_index_pairs"]
    projected_bytes = total_bytes / expected * annual_pairs
    thresholds = config["acceptance_thresholds"]
    invalid_values = [
        row
        for row in success
        if not math.isfinite(row["decoded"]["temperature_f"])
        or not (
            thresholds["temperature_f_minimum"]
            <= row["decoded"]["temperature_f"]
            <= thresholds["temperature_f_maximum"]
        )
    ]
    distant = [
        row
        for row in success
        if row["decoded"]["coordinate_delta_degrees"]
        > thresholds["nearest_grid_distance_degrees_maximum"]
    ]
    summary = {
        "expected_message_count": expected,
        "successful_message_count": len(success),
        "failed_message_count": len(failed),
        "success_rate": len(success) / expected,
        "nonfinite_or_implausible_count": len(invalid_values),
        "distant_gridpoint_count": len(distant),
        "pilot_range_byte_count": total_bytes,
        "mean_range_bytes_per_message": total_bytes / len(success) if success else None,
        "annual_projected_range_bytes": projected_bytes,
        "annual_projected_range_gib": projected_bytes / 1024**3,
        "annual_projected_range_get_count": annual_pairs,
        "recovered_error_count": sum(len(row["errors"]) for row in success),
    }
    summary["passed"] = (
        summary["success_rate"]
        >= thresholds["successful_index_range_decode_rate"]
        and not invalid_values
        and not distant
        and summary["annual_projected_range_gib"]
        <= thresholds["annual_projected_range_bytes_maximum_gib"]
        and annual_pairs
        <= thresholds["annual_projected_range_get_count_maximum"]
    )
    artifact = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "config": str(args.config),
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "summary": summary,
        "rows": rows,
    }
    result_path = args.output_dir / "result.json"
    result_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
