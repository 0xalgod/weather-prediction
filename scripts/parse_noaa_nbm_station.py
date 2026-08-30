#!/usr/bin/env python3
"""Parse station MaxT distributions from immutable NBM probe files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import parse_station_maxt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--station", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError("parsed output must be immutable")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sources = []
    records = []
    for source in manifest["records"]:
        path = Path(source["retrieval"]["local_path"])
        parsed = parse_station_maxt(path, args.station, source["model_run_time_utc"])
        sources.append(
            {
                "run_date": source["run_date"],
                "cycle_utc": source["cycle_utc"],
                "sha256": source["retrieval"]["sha256"],
                "http_last_modified": source["retrieval"]["http_last_modified"],
                "ingested_at_utc": source["retrieval"]["received_at_utc"],
                "nbm_version": parsed["nbm_version"],
                "record_count": len(parsed["records"]),
            }
        )
        for record in parsed["records"]:
            records.append(
                {
                    **record,
                    "source_sha256": source["retrieval"]["sha256"],
                    "source_http_last_modified": source["retrieval"]["http_last_modified"],
                    "ingested_at_utc": source["retrieval"]["received_at_utc"],
                }
            )
    output = {
        "schema_version": "0.1.0",
        "source_manifest": str(args.manifest),
        "station_code": args.station,
        "sources": sources,
        "record_count": len(records),
        "missing_value_count": sum(
            value is None
            for record in records
            for key, value in record.items()
            if key.endswith("_f")
        ),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in output if key != "records"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
