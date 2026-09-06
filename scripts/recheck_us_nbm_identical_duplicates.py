#!/usr/bin/env python3
"""Recheck frozen NBM objects with exact-identical duplicate canonicalization."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import (
    extract_canonical_station_block,
    parse_station_maxt,
    publication_is_admissible,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_date(run_date: str) -> str:
    return (datetime.strptime(run_date, "%Y%m%d").date() + timedelta(days=1)).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")

    config = json.loads(args.config.read_text())
    source = Path(config["source_raw_run"])
    source_result_path = source / "result.json"
    source_result = json.loads(source_result_path.read_text())
    retrievals = {
        row["record"]["run_date"]: row for row in source_result["retrievals"]
    }
    args.output.mkdir(parents=True)
    rows = []
    conflict_count = 0
    required = tuple(config["probe"]["required_fields"])

    for target in config["probe"]["target_dates"]:
        run_date = (datetime.fromisoformat(target).date() - timedelta(days=1)).strftime("%Y%m%d")
        item = retrievals[run_date]
        retrieval = item["retrieval"]
        full_path = Path(item["destination"])
        decision = datetime.strptime(run_date, "%Y%m%d").replace(hour=11, tzinfo=timezone.utc)
        admissible = publication_is_admissible(
            retrieval["http_last_modified"], decision.isoformat()
        )
        content = full_path.read_bytes()
        for station in config["probe"]["stations"]:
            destination = args.output / "stations" / run_date / f"{station}.nbptx"
            error = None
            feature = None
            diagnostic = None
            try:
                block, diagnostic = extract_canonical_station_block(content, station)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(block)
                run_time = datetime.strptime(run_date, "%Y%m%d").replace(
                    hour=config["probe"]["cycle_utc"], tzinfo=timezone.utc
                )
                parsed = parse_station_maxt(destination, station, run_time.isoformat())
                matches = [
                    record
                    for record in parsed["records"]
                    if record["forecast_hour"] == config["probe"]["forecast_hour"]
                ]
                if len(matches) != 1:
                    raise ValueError("expected exactly one locked forecast-hour record")
                feature = matches[0]
                if any(feature[field] is None for field in required):
                    raise ValueError("required field is missing")
            except (UnicodeDecodeError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                if "conflicting duplicate" in str(exc):
                    conflict_count += 1
            rows.append(
                {
                    "run_date": run_date,
                    "target_date": target_date(run_date),
                    "station_code": station,
                    "publication_admissible": admissible,
                    "source_full_object_path": str(full_path),
                    "source_full_object_sha256": sha256(full_path),
                    "source_last_modified": retrieval["http_last_modified"],
                    "canonicalization": diagnostic,
                    "station_block_path": str(destination) if destination.exists() else None,
                    "feature": feature,
                    "error": error,
                    "passed": admissible and error is None,
                }
            )

    expected = config["evaluation"]["expected_station_date_count"]
    passed = [row for row in rows if row["passed"]]
    summary = {
        "station_regime_count": len({row["station_code"] for row in rows}),
        "probe_date_count": len({row["target_date"] for row in rows}),
        "expected_station_date_count": expected,
        "passed_station_date_count": len(passed),
        "station_date_block_coverage": len(passed) / expected,
        "required_field_coverage": len(passed) / expected,
        "source_duplicate_block_set_count": sum(
            bool(row["canonicalization"] and row["canonicalization"]["identical_duplicate"])
            for row in rows
        ),
        "conflicting_duplicate_count": conflict_count,
        "temporal_leakage_count": sum(not row["publication_admissible"] for row in rows),
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
        "maximum_conflicting_duplicate_count": conflict_count
        <= gates["maximum_conflicting_duplicate_count"],
        "maximum_temporal_leakage_count": summary["temporal_leakage_count"]
        <= gates["maximum_temporal_leakage_count"],
    }
    (args.output / "station-dates.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_result_sha256": sha256(source_result_path),
        "summary": summary,
        "checks": checks,
        "decision": (
            "US_NBM_STATION_COVERAGE_PASS"
            if all(checks.values())
            else "US_NBM_STATION_COVERAGE_FAIL"
        ),
        "rows": rows,
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
