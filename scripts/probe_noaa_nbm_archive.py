#!/usr/bin/env python3
"""Retrieve current and historical NBM probabilistic text products as issued."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import (
    download_public_object,
    inspect_probabilistic_text,
    probabilistic_text_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", action="append", required=True)
    parser.add_argument("--cycle", type=int, default=0)
    parser.add_argument("--station", default="KORD")
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.raw_directory.exists() or args.output.exists():
        raise FileExistsError("NBM probe outputs require unused immutable paths")
    args.raw_directory.mkdir(parents=True)
    records = []
    for run_date in args.run_date:
        destination = args.raw_directory / f"blend.{run_date}.t{args.cycle:02d}z.nbptx"
        retrieval = download_public_object(
            probabilistic_text_url(run_date, args.cycle), destination
        )
        records.append(
            {
                "run_date": run_date,
                "cycle_utc": args.cycle,
                "model_run_time_utc": datetime.strptime(
                    f"{run_date}{args.cycle:02d}", "%Y%m%d%H"
                )
                .replace(tzinfo=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "retrieval": retrieval,
                "inventory": inspect_probabilistic_text(destination, args.station),
            }
        )
    output = {
        "schema_version": "0.1.0",
        "source": "NOAA NBM probabilistic text via public AWS",
        "station_probe": args.station,
        "records": records,
        "all_http_200": all(record["retrieval"]["http_status"] == 200 for record in records),
        "all_checksums_unique": len({record["retrieval"]["sha256"] for record in records})
        == len(records),
        "all_station_present": all(
            record["inventory"]["station_occurrence_count"] > 0 for record in records
        ),
        "all_maxt_markers_present": all(
            record["inventory"]["contains_probabilistic_maxt_markers"] for record in records
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
