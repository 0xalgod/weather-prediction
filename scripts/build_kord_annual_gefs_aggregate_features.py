#!/usr/bin/env python3
"""Build annual compact KORD GEFS mean/spread features."""

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

from weather_quant.ingestion.noaa_gefs import (
    aggregate_object_url,
    decode_nearest_tmax,
    download_selected_ranges,
    fetch_inventory,
    local_day_tmax_steps,
    parse_max_window,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--attempts", type=int, default=3)
    return parser.parse_args()


def dates_inclusive(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def retrieve(task: dict, station: dict, output_dir: Path, attempts: int) -> dict:
    run_key = task["run_date"].replace("-", "")
    url = aggregate_object_url(run_key, 0, task["product"], task["step"])
    errors = []
    destination = (
        output_dir
        / "messages"
        / task["target_date"]
        / task["product"]
        / f"f{task['step']:03d}-tmax.grib2"
    )
    for attempt in range(1, attempts + 1):
        try:
            inventory = fetch_inventory(url, timeout=90)
            rows = [
                row
                for row in inventory["inventory"]["selected_rows"]
                if row["parameter"] == "TMAX" and row["level"] == "2 m above ground"
            ]
            if len(rows) != 1:
                raise ValueError("expected exactly one aggregate 2 m TMAX row")
            start_hour, end_hour = parse_max_window(rows[0]["forecast_window"])
            if (start_hour, end_hour) != (task["step"] - 6, task["step"]):
                raise ValueError("aggregate TMAX is not canonical six-hour window")
            expected_semantic = (
                "ens mean" if task["product"] == "geavg" else "ens std dev"
            )
            if rows[0]["ensemble"] != expected_semantic:
                raise ValueError("aggregate index ensemble semantic mismatch")
            published = datetime.strptime(
                inventory["http_last_modified"], "%a, %d %b %Y %H:%M:%S %Z"
            ).replace(tzinfo=timezone.utc)
            decision = datetime.fromisoformat(task["run_date"] + "T11:00:00+00:00")
            if published > decision:
                raise ValueError("aggregate object published after decision time")
            inventory["inventory"]["selected_rows"] = rows
            retrieval = download_selected_ranges(inventory, destination, timeout=90)
            decoded = decode_nearest_tmax(
                destination, station["latitude"], station["longitude"]
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
                "index_sha256": inventory["index_sha256"],
                "object_etag": inventory["http_etag"],
                "object_last_modified": inventory["http_last_modified"],
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


def summarize_day(target: date, semantics: dict, rows: list[dict]) -> dict:
    success = [row for row in rows if row["status"] == "SUCCESS"]
    by_key = {(row["product"], row["step"]): row["value_f"] for row in success}
    expected = len(semantics["overlap_steps"]) * 2
    complete = len(success) == expected
    result = {
        "target_date": target.isoformat(),
        "complete": complete,
        "exact_partition": semantics["exact_partition"],
        "outside_local_seconds": semantics["outside_local_seconds"],
        "overlap_steps": semantics["overlap_steps"],
        "interior_steps": semantics["interior_steps"],
        "message_success_count": len(success),
        "message_expected_count": expected,
    }
    if complete:
        overlap_peak_step = max(
            semantics["overlap_steps"], key=lambda step: by_key[("geavg", step)]
        )
        interior_peak_step = max(
            semantics["interior_steps"], key=lambda step: by_key[("geavg", step)]
        )
        result["features"] = {
            "gefs_overlap_mean_max_f": by_key[("geavg", overlap_peak_step)],
            "gefs_overlap_spread_at_mean_max_f": by_key[("gespr", overlap_peak_step)],
            "gefs_overlap_peak_step": overlap_peak_step,
            "gefs_interior_mean_max_f": by_key[("geavg", interior_peak_step)],
            "gefs_interior_spread_at_mean_max_f": by_key[("gespr", interior_peak_step)],
            "gefs_interior_peak_step": interior_peak_step,
            "gefs_max_block_spread_f": max(
                by_key[("gespr", step)] for step in semantics["overlap_steps"]
            ),
        }
    return result


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError("annual aggregate output must be immutable")
    config_raw = args.config.read_bytes()
    config = json.loads(config_raw)
    policy = config["annual_gefs_aggregate_ingestion"]
    scope = config["scope"]
    targets = dates_inclusive(
        date.fromisoformat(scope["target_start_date"]),
        date.fromisoformat(scope["target_end_date"]),
    )
    excluded = set(policy["publication_excluded_target_dates"])
    admitted = [target for target in targets if target.isoformat() not in excluded]
    if len(admitted) != policy["expected_admissible_target_dates"]:
        raise ValueError("annual aggregate admitted-date count changed")
    tasks = []
    semantics_by_date = {}
    for target in admitted:
        semantics = local_day_tmax_steps(target, scope["timezone"])
        semantics_by_date[target.isoformat()] = semantics
        run_date = (target - timedelta(days=1)).isoformat()
        for step in semantics["overlap_steps"]:
            for product in config["features"]["gefs"]["products"]:
                tasks.append(
                    {
                        "target_date": target.isoformat(),
                        "run_date": run_date,
                        "step": step,
                        "product": product,
                    }
                )
    if len(tasks) != policy["expected_message_count"]:
        raise ValueError("annual aggregate message count changed")
    args.output_dir.mkdir(parents=True)
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                retrieve,
                task,
                {
                    "latitude": 41.96019,
                    "longitude": -87.93162,
                },
                args.output_dir,
                args.attempts,
            ): task
            for task in tasks
        }
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: (row["target_date"], row["step"], row["product"]))
    rows_by_date: dict[str, list[dict]] = {}
    for row in rows:
        rows_by_date.setdefault(row["target_date"], []).append(row)
    daily = [
        summarize_day(
            target,
            semantics_by_date[target.isoformat()],
            rows_by_date[target.isoformat()],
        )
        for target in admitted
    ]
    success = [row for row in rows if row["status"] == "SUCCESS"]
    finite_plausible = all(
        math.isfinite(row["value_f"])
        and (
            policy["temperature_f_minimum"]
            <= row["value_f"]
            <= policy["temperature_f_maximum"]
            if row["product"] == "geavg"
            else policy["spread_f_minimum"]
            <= row["value_f"]
            <= policy["spread_f_maximum"]
        )
        for row in success
    )
    summary = {
        "target_date_count": len(targets),
        "publication_excluded_date_count": len(excluded),
        "admitted_target_date_count": len(admitted),
        "expected_message_count": len(tasks),
        "successful_message_count": len(success),
        "failed_message_count": len(tasks) - len(success),
        "message_success_rate": len(success) / len(tasks),
        "complete_day_count": sum(day["complete"] for day in daily),
        "exact_complete_day_count": sum(
            day["complete"] and day["exact_partition"] for day in daily
        ),
        "proxy_complete_day_count": sum(
            day["complete"] and not day["exact_partition"] for day in daily
        ),
        "finite_plausible": finite_plausible,
        "range_byte_count": sum(row["retrieval"]["byte_count"] for row in success),
        "recovered_error_count": sum(len(row["errors"]) for row in success),
    }
    summary["passed"] = (
        summary["message_success_rate"] >= policy["message_success_rate_minimum"]
        and finite_plausible
        and summary["complete_day_count"] / len(admitted)
        >= config["quality_gates"]["gefs_complete_member_rate_minimum"]
    )
    artifact = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "substep": "annual_gefs_aggregate_features",
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "config": str(args.config),
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "summary": summary,
        "publication_excluded_target_dates": sorted(excluded),
        "daily_features": daily,
        "rows": rows,
    }
    result = args.output_dir / "result.json"
    result.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
