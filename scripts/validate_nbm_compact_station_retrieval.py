#!/usr/bin/env python3
"""Validate one compact NBM station range against an accepted full object."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import (
    download_station_range,
    extract_station_block,
    parse_station_maxt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--full-object", type=Path, required=True)
    parser.add_argument("--model-run-time-utc", required=True)
    parser.add_argument("--station", default="KORD")
    parser.add_argument("--byte-start", type=int, required=True)
    parser.add_argument("--byte-end", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError("validation output directory must be immutable")
    compact_path = args.output_dir / f"{args.station}.nbptx"
    retrieval = download_station_range(
        args.url,
        args.station,
        args.byte_start,
        args.byte_end,
        compact_path,
    )
    full_bytes = args.full_object.read_bytes()
    expected_block = extract_station_block(full_bytes, args.station)
    actual_block = compact_path.read_bytes()
    expected_sha = hashlib.sha256(expected_block).hexdigest()
    actual_sha = hashlib.sha256(actual_block).hexdigest()
    parsed = parse_station_maxt(compact_path, args.station, args.model_run_time_utc)
    exact_match = expected_block == actual_block
    artifact = {
        "schema_version": "1.0.0",
        "experiment_id": "EXP-20260905-kord-forecast-dataset-v1",
        "substep": "nbm_compact_station_retrieval_validation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_full_object": str(args.full_object),
        "source_full_object_sha256": hashlib.sha256(full_bytes).hexdigest(),
        "retrieval": retrieval,
        "comparison": {
            "expected_station_block_sha256": expected_sha,
            "actual_station_block_sha256": actual_sha,
            "exact_byte_match": exact_match,
            "parsed_record_count": len(parsed["records"]),
            "nbm_version": parsed["nbm_version"],
            "required_target_record_count": sum(
                record["forecast_hour"] == 41 for record in parsed["records"]
            ),
        },
        "passed": exact_match
        and len(parsed["records"]) > 0
        and sum(record["forecast_hour"] == 41 for record in parsed["records"]) == 1,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "result.json"
    result_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "result": str(result_path),
        **artifact["comparison"],
        "passed": artifact["passed"],
    }
    print(json.dumps(summary, indent=2))
    if not artifact["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
