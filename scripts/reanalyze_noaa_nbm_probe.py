#!/usr/bin/env python3
"""Re-run station-block inventory against immutable NBM files in a probe manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import inspect_probabilistic_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError("analysis output must be immutable")
    source = json.loads(args.input.read_text(encoding="utf-8"))
    records = []
    for record in source["records"]:
        path = Path(record["retrieval"]["local_path"])
        actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(
            {
                "run_date": record["run_date"],
                "cycle_utc": record["cycle_utc"],
                "model_run_time_utc": record["model_run_time_utc"],
                "retrieval": record["retrieval"],
                "checksum_reverified": actual_sha256 == record["retrieval"]["sha256"],
                "inventory": inspect_probabilistic_text(path, source["station_probe"]),
            }
        )
    output = {
        "schema_version": "0.2.0",
        "source_manifest": str(args.input),
        "station_probe": source["station_probe"],
        "records": records,
        "all_checksums_reverified": all(record["checksum_reverified"] for record in records),
        "all_station_blocks_present": all(
            record["inventory"]["station_occurrence_count"] == 1 for record in records
        ),
        "all_station_blocks_have_maxt_markers": all(
            record["inventory"]["contains_probabilistic_maxt_markers"] for record in records
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
