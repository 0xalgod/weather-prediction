#!/usr/bin/env python3
"""Evaluate NBM daytime MaxT windows against US city-local market days."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def station_from_resolution_url(url: str) -> str:
    parsed = urlparse(url)
    query_station = parse_qs(parsed.query).get("site", [None])[0]
    station = (query_station or Path(parsed.path).name).upper()
    if len(station) != 4 or not station.isalnum():
        raise ValueError(f"invalid resolution station in URL: {url}")
    return station


def overlap_hours(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> float:
    start = max(start_a, start_b)
    end = min(end_a, end_b)
    return max(0.0, (end - start).total_seconds() / 3600)


def evaluate_window(target: str, timezone_name: str, nbm_offsets: list[int]) -> dict:
    target_day = date.fromisoformat(target)
    zone = ZoneInfo(timezone_name)
    local_start = datetime.combine(target_day, time.min, zone)
    local_end = datetime.combine(target_day + timedelta(days=1), time.min, zone)
    market_start = local_start.astimezone(timezone.utc)
    market_end = local_end.astimezone(timezone.utc)
    target_00z = datetime.combine(target_day, time.min, timezone.utc)
    nbm_start = target_00z + timedelta(hours=nbm_offsets[0])
    nbm_end = target_00z + timedelta(hours=nbm_offsets[1])
    overlap = overlap_hours(market_start, market_end, nbm_start, nbm_end)
    market_duration = (market_end - market_start).total_seconds() / 3600
    nbm_duration = (nbm_end - nbm_start).total_seconds() / 3600
    return {
        "target_date": target,
        "timezone": timezone_name,
        "utc_offset_at_local_start_hours": local_start.utcoffset().total_seconds() / 3600,
        "utc_offset_at_local_end_hours": local_end.utcoffset().total_seconds() / 3600,
        "market_start_utc": market_start.isoformat().replace("+00:00", "Z"),
        "market_end_utc": market_end.isoformat().replace("+00:00", "Z"),
        "market_duration_hours": market_duration,
        "nbm_start_utc": nbm_start.isoformat().replace("+00:00", "Z"),
        "nbm_end_utc": nbm_end.isoformat().replace("+00:00", "Z"),
        "nbm_duration_hours": nbm_duration,
        "overlap_hours": overlap,
        "market_hours_missing_from_nbm": market_duration - overlap,
        "nbm_hours_outside_market": nbm_duration - overlap,
        "exact_window_equivalence": market_start == nbm_start and market_end == nbm_end,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")

    config = json.loads(args.config.read_text())
    inventory_path = Path(config["source_inventory"])
    inventory = json.loads(inventory_path.read_text())
    expected_by_city = {
        city: set(details.get("stations", [details.get("station")]))
        for city, details in config["cities"].items()
    }
    observed_by_city = {city: set() for city in config["cities"]}
    for row in inventory["rows"]:
        city = row["city"]
        if city in observed_by_city:
            observed_by_city[city].add(station_from_resolution_url(row["resolution_source"]))
    mismatches = {
        city: {"expected": sorted(expected_by_city[city]), "observed": sorted(observed)}
        for city, observed in observed_by_city.items()
        if observed != expected_by_city[city]
    }

    offsets = config["probe"]["nbm_window_offsets_from_target_00z_utc_hours"]
    rows = []
    conversion_errors = []
    for city, details in config["cities"].items():
        for target in config["probe"]["target_dates"]:
            try:
                row = evaluate_window(target, details["timezone"], offsets)
                rows.append({"city": city, "stations": sorted(expected_by_city[city]), **row})
            except (ValueError, ZoneInfoNotFoundError) as exc:
                conversion_errors.append({"city": city, "target_date": target, "error": str(exc)})

    exact_count = sum(row["exact_window_equivalence"] for row in rows)
    summary = {
        "city_count": len(config["cities"]),
        "city_date_count": len(rows),
        "minimum_overlap_hours": min(row["overlap_hours"] for row in rows),
        "maximum_overlap_hours": max(row["overlap_hours"] for row in rows),
        "maximum_market_hours_missing_from_nbm": max(
            row["market_hours_missing_from_nbm"] for row in rows
        ),
        "maximum_nbm_hours_outside_market_window": max(
            row["nbm_hours_outside_market"] for row in rows
        ),
        "timezone_conversion_error_count": len(conversion_errors),
        "station_resolution_mismatch_count": len(mismatches),
        "exact_window_equivalence_count": exact_count,
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_city_count": summary["city_count"] == gates["exact_city_count"],
        "exact_city_date_count": summary["city_date_count"] == gates["exact_city_date_count"],
        "minimum_overlap_hours": summary["minimum_overlap_hours"]
        >= gates["minimum_overlap_hours"],
        "maximum_nbm_hours_outside_market_window": summary[
            "maximum_nbm_hours_outside_market_window"
        ]
        <= gates["maximum_nbm_hours_outside_market_window"],
        "maximum_timezone_conversion_error_count": len(conversion_errors)
        <= gates["maximum_timezone_conversion_error_count"],
        "maximum_station_resolution_mismatch_count": len(mismatches)
        <= gates["maximum_station_resolution_mismatch_count"],
        "expected_exact_window_equivalence_count": exact_count
        == gates["expected_exact_window_equivalence_count"],
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_inventory_sha256": sha256(inventory_path),
        "summary": summary,
        "checks": checks,
        "decision": "PROXY_18H_MAX_PASS" if all(checks.values()) else "PROXY_18H_MAX_FAIL",
        "station_identity_mismatches": mismatches,
        "timezone_conversion_errors": conversion_errors,
        "rows": rows,
        "boundary": config["boundary"],
    }
    args.output.mkdir(parents=True)
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
