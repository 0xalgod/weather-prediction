#!/usr/bin/env python3
"""Create deterministic closed-market anomaly cohorts and reconciliation sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from weather_quant.ingestion.closed_market_audit import (
    build_closed_audit,
    classify_closed_event,
    iter_raw_events,
    select_stratified_sample,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = [classify_closed_event(event, checksum) for event, checksum in iter_raw_events(args.raw_directory)]
    audit = build_closed_audit(records)
    sample, sampling = select_stratified_sample(records)
    output = {
        "schema_version": "0.1.0",
        "source_run_directory": str(args.raw_directory),
        "audit": audit,
        "sampling": sampling,
        "manual_reconciliation_sample": sample,
    }
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"audit": audit, "sampling": sampling}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
