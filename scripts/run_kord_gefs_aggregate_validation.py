#!/usr/bin/env python3
"""Validate GEFS mean/spread products against full-member pilot values."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_gefs import (
    aggregate_object_url,
    decode_nearest_tmax,
    download_selected_ranges,
    fetch_inventory,
    parse_max_window,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retrieve(task: dict, station: dict, output_dir: Path) -> dict:
    run_key = task["run_date"].replace("-", "")
    url = aggregate_object_url(run_key, 0, task["product"], task["step"])
    inventory = fetch_inventory(url, timeout=90)
    rows = [
        row
        for row in inventory["inventory"]["selected_rows"]
        if row["parameter"] == "TMAX" and row["level"] == "2 m above ground"
    ]
    if len(rows) != 1:
        raise ValueError("expected exactly one aggregate 2 m TMAX row")
    start, end = parse_max_window(rows[0]["forecast_window"])
    if (start, end) != (task["step"] - 6, task["step"]):
        raise ValueError("aggregate TMAX is not canonical six-hour window")
    expected_ensemble = "ens mean" if task["product"] == "geavg" else "ens std dev"
    if rows[0]["ensemble"] != expected_ensemble:
        raise ValueError("aggregate index ensemble semantic mismatch")
    published = datetime.strptime(
        inventory["http_last_modified"], "%a, %d %b %Y %H:%M:%S %Z"
    ).replace(tzinfo=timezone.utc)
    decision = datetime.fromisoformat(task["run_date"] + "T11:00:00+00:00")
    if published > decision:
        raise ValueError("aggregate object published after decision time")
    inventory["inventory"]["selected_rows"] = rows
    destination = (
        output_dir
        / task["target_date"]
        / task["product"]
        / f"f{task['step']:03d}-tmax.grib2"
    )
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
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError("aggregate validation output must be immutable")
    config_raw = args.config.read_bytes()
    config = json.loads(config_raw)
    pilot_path = Path(config["source_full_member_pilot"])
    if sha256_path(pilot_path) != config["source_full_member_pilot_sha256"]:
        raise ValueError("full-member pilot checksum mismatch")
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    member_values: dict[tuple[str, int], list[float]] = {}
    for row in pilot["rows"]:
        if row["status"] == "SUCCESS":
            key = (row["target_date"], row["step"])
            member_values.setdefault(key, []).append(row["decoded"]["temperature_f"])
    tasks = [
        {
            "target_date": case["target_date"],
            "run_date": case["run_date"],
            "regime": case["regime"],
            "step": step,
            "product": product,
        }
        for case in config["cases"]
        for step in case["steps"]
        for product in ("geavg", "gespr")
    ]
    if len(tasks) != 18:
        raise ValueError("expected exact 18 aggregate tasks")
    args.output_dir.mkdir(parents=True)
    aggregate_rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(retrieve, task, config["station"], args.output_dir): task
            for task in tasks
        }
        for future in as_completed(futures):
            aggregate_rows.append(future.result())
    aggregate_rows.sort(
        key=lambda row: (row["target_date"], row["step"], row["product"])
    )
    by_aggregate = {
        (row["target_date"], row["step"], row["product"]): row
        for row in aggregate_rows
    }
    comparisons = []
    for key, values in sorted(member_values.items()):
        target, step = key
        member_count = len(values)
        empirical_mean = statistics.mean(values)
        empirical_spread = statistics.pstdev(values)
        mean_value = by_aggregate[(target, step, "geavg")]["value_f"]
        spread_value = by_aggregate[(target, step, "gespr")]["value_f"]
        comparisons.append(
            {
                "target_date": target,
                "step": step,
                "member_count": member_count,
                "primary": member_count == 31,
                "empirical_mean_f": empirical_mean,
                "geavg_f": mean_value,
                "mean_error_f": mean_value - empirical_mean,
                "empirical_population_spread_f": empirical_spread,
                "gespr_f": spread_value,
                "spread_error_f": spread_value - empirical_spread,
            }
        )
    primary = [row for row in comparisons if row["primary"]]
    mean_errors = [abs(row["mean_error_f"]) for row in primary]
    spread_errors = [abs(row["spread_error_f"]) for row in primary]
    pilot_bytes = sum(row["retrieval"]["byte_count"] for row in aggregate_rows)
    projected_gets = round(
        config["annual_projection"]["admissible_member_step_count"]
        * config["annual_projection"]["aggregate_to_member_product_ratio"]
    )
    projected_bytes = pilot_bytes / len(aggregate_rows) * projected_gets
    thresholds = config["acceptance_thresholds"]
    summary = {
        "aggregate_message_count": len(aggregate_rows),
        "primary_complete_cell_count": len(primary),
        "mean_mae_f": statistics.mean(mean_errors),
        "mean_max_absolute_error_f": max(mean_errors),
        "spread_mae_f": statistics.mean(spread_errors),
        "spread_max_absolute_error_f": max(spread_errors),
        "pilot_range_byte_count": pilot_bytes,
        "annual_projected_range_get_count": projected_gets,
        "annual_projected_range_gib": projected_bytes / 1024**3,
    }
    summary["passed"] = (
        len(aggregate_rows) == 18
        and len(primary) == thresholds["primary_complete_cell_count_exact"]
        and summary["mean_mae_f"] <= thresholds["mean_absolute_error_mean_f_maximum"]
        and summary["mean_max_absolute_error_f"]
        <= thresholds["maximum_absolute_error_mean_f_maximum"]
        and summary["spread_mae_f"]
        <= thresholds["mean_absolute_error_spread_f_maximum"]
        and summary["spread_max_absolute_error_f"]
        <= thresholds["maximum_absolute_error_spread_f_maximum"]
        and summary["annual_projected_range_gib"]
        <= thresholds["annual_projected_range_gib_maximum"]
        and projected_gets
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
        "source_full_member_pilot_sha256": config["source_full_member_pilot_sha256"],
        "summary": summary,
        "comparisons": comparisons,
        "aggregate_rows": aggregate_rows,
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
