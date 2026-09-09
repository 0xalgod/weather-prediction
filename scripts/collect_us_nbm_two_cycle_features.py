#!/usr/bin/env python3
"""Collect and validate frozen 07Z/13Z NBM features."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.probe_us_nbm_13z_coverage import retrieve
from weather_quant.ingestion.noaa_nbm import (
    extract_canonical_station_block,
    parse_station_maxt,
    publication_is_admissible,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    cfg = json.loads(args.config.read_text())
    cohort, transport = cfg["cohort"], cfg["transport"]
    args.output.mkdir(parents=True)
    full = args.output / "full_objects"
    full.mkdir()
    jobs = []
    with ThreadPoolExecutor(max_workers=transport["workers"]) as pool:
        for target in cohort["target_dates"]:
            run = (
                (datetime.fromisoformat(target).date())
                .fromordinal(datetime.fromisoformat(target).date().toordinal() - 1)
                .strftime("%Y%m%d")
            )
            for cycle in cohort["cycles"]:
                local_cfg = {"probe": {"cycle_utc": cycle["cycle_utc"]}, "transport": transport}
                dest = full / f"blend_nbptx.{run}.t{cycle['cycle_utc']:02d}z"
                jobs.append((pool.submit(retrieve, target, dest, local_cfg), cycle))
        retrievals = []
        for future, cycle in jobs:
            item = future.result()
            item["cycle_utc"] = cycle["cycle_utc"]
            item["forecast_hour"] = cycle["forecast_hour"]
            retrievals.append(item)
    retrievals.sort(key=lambda x: (x["target_date"], x["cycle_utc"]))

    rows, conflicts = [], 0
    for item in retrievals:
        r = item["retrieval"]
        cutoff = datetime.strptime(item["run_date"], "%Y%m%d").replace(hour=18, tzinfo=timezone.utc)
        for station in cohort["stations"]:
            feature = diagnostic = None
            error = None
            admissible = (
                False
                if r is None
                else publication_is_admissible(r["http_last_modified"], cutoff.isoformat())
            )
            try:
                if r is None:
                    raise ValueError("FULL_OBJECT_RETRIEVAL_FAILED")
                block, diagnostic = extract_canonical_station_block(
                    Path(r["local_path"]).read_bytes(), station
                )
                station_path = (
                    args.output
                    / "stations"
                    / item["run_date"]
                    / f"t{item['cycle_utc']:02d}z"
                    / f"{station}.nbptx"
                )
                station_path.parent.mkdir(parents=True, exist_ok=True)
                station_path.write_bytes(block)
                model_run = datetime.strptime(item["run_date"], "%Y%m%d").replace(
                    hour=item["cycle_utc"], tzinfo=timezone.utc
                )
                parsed = parse_station_maxt(station_path, station, model_run.isoformat())
                matches = [
                    x for x in parsed["records"] if x["forecast_hour"] == item["forecast_hour"]
                ]
                if len(matches) != 1:
                    raise ValueError("expected exactly one forecast-hour feature")
                feature = matches[0]
                if any(feature[k] is None for k in cohort["required_fields"]):
                    raise ValueError("required field missing")
            except (UnicodeDecodeError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                conflicts += "conflicting duplicate" in str(exc)
            rows.append(
                {
                    "target_date": item["target_date"],
                    "run_date": item["run_date"],
                    "cycle_utc": item["cycle_utc"],
                    "forecast_hour": item["forecast_hour"],
                    "station_code": station,
                    "publication_cutoff_utc": cutoff.isoformat(),
                    "source_last_modified": None if r is None else r["http_last_modified"],
                    "publication_admissible": admissible,
                    "canonicalization": diagnostic,
                    "feature": feature,
                    "passed": admissible and error is None,
                    "error": error,
                }
            )
    expected = len(cohort["target_dates"]) * len(cohort["cycles"]) * len(cohort["stations"])
    transfer = sum(x["retrieval"]["byte_count"] for x in retrievals if x["retrieval"])
    summary = {
        "target_date_count": len(cohort["target_dates"]),
        "cycle_count": len(cohort["cycles"]),
        "station_count": len(cohort["stations"]),
        "full_object_count": len(retrievals),
        "expected_station_cycle_date_count": expected,
        "passed_station_cycle_date_count": sum(x["passed"] for x in rows),
        "station_cycle_date_feature_rate": sum(x["passed"] for x in rows) / expected,
        "retrieval_failure_count": sum(x["retrieval"] is None for x in retrievals),
        "station_error_count": sum(x["error"] is not None for x in rows),
        "publication_after_cutoff_count": sum(x["publication_admissible"] is False for x in rows),
        "conflicting_duplicate_count": conflicts,
        "transfer_bytes": transfer,
    }
    g = cfg["acceptance_thresholds"]
    checks = {
        "exact_target_date_count": summary["target_date_count"] == g["exact_target_date_count"],
        "exact_cycle_count": summary["cycle_count"] == g["exact_cycle_count"],
        "exact_station_count": summary["station_count"] == g["exact_station_count"],
        "exact_full_object_count": summary["full_object_count"] == g["exact_full_object_count"],
        "minimum_station_cycle_date_feature_rate": summary["station_cycle_date_feature_rate"]
        >= g["minimum_station_cycle_date_feature_rate"],
        "maximum_retrieval_failure_count": summary["retrieval_failure_count"]
        <= g["maximum_retrieval_failure_count"],
        "maximum_station_error_count": summary["station_error_count"]
        <= g["maximum_station_error_count"],
        "maximum_publication_after_cutoff_count": summary["publication_after_cutoff_count"]
        <= g["maximum_publication_after_cutoff_count"],
        "maximum_conflicting_duplicate_count": conflicts
        <= g["maximum_conflicting_duplicate_count"],
        "maximum_transfer_bytes": transfer <= g["maximum_transfer_bytes"],
    }
    (args.output / "station-cycle-dates.jsonl").write_text(
        "".join(json.dumps(x, sort_keys=True) + "\n" for x in rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": cfg["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "summary": summary,
        "checks": checks,
        "decision": "NBM_TWO_CYCLE_ACQUISITION_PASS"
        if all(checks.values())
        else "NBM_TWO_CYCLE_ACQUISITION_FAIL",
        "retrievals": retrievals,
        "boundary": cfg["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "retrievals"}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
