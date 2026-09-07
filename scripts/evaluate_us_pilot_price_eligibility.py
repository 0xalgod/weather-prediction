#!/usr/bin/env python3
"""Apply the locked real-time price eligibility rule to the frozen US pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligibility_reason(row: dict) -> str:
    if not row["complete_vector"]:
        return "NO_TRADE_INCOMPLETE_VECTOR"
    if not row["usable_full_vector"]:
        return "NO_TRADE_STALE_VECTOR"
    return "PRICE_ELIGIBLE"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source = Path(config["source_price_run"])
    result_path = source / "result.json"
    if sha256(result_path) != config["source_result_sha256"]:
        raise ValueError("source result checksum mismatch")
    source_result = json.loads(result_path.read_text())
    rows = [
        json.loads(line)
        for line in (source / "event-horizon-coverage.jsonl").read_text().splitlines()
    ]
    classified = [{**row, "eligibility": eligibility_reason(row)} for row in rows]
    eligible = [row for row in classified if row["eligibility"] == "PRICE_ELIGIBLE"]
    city_counts = Counter(row["city"] for row in eligible)
    duplicate_count = len(rows) - len({str(row["event_id"]) for row in rows})
    summary = {
        "source_event_count": len(rows),
        "eligible_event_count": len(eligible),
        "no_trade_event_count": len(rows) - len(eligible),
        "eligible_target_date_count": len({row["target_date"] for row in eligible}),
        "city_count": len(city_counts),
        "minimum_eligible_event_count_per_city": min(city_counts.values()),
        "eligible_event_count_by_city": dict(sorted(city_counts.items())),
        "eligibility_reason_counts": dict(
            sorted(Counter(row["eligibility"] for row in classified).items())
        ),
        "request_error_count": source_result["summary"]["request_error_count"],
        "temporal_leakage_count": source_result["summary"]["temporal_leakage_count"],
        "duplicate_event_count": duplicate_count,
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "minimum_eligible_event_count": summary["eligible_event_count"]
        >= gates["minimum_eligible_event_count"],
        "minimum_eligible_target_date_count": summary["eligible_target_date_count"]
        >= gates["minimum_eligible_target_date_count"],
        "minimum_eligible_event_count_per_city": summary[
            "minimum_eligible_event_count_per_city"
        ]
        >= gates["minimum_eligible_event_count_per_city"],
        "exact_city_count": summary["city_count"] == gates["exact_city_count"],
        "maximum_request_error_count": summary["request_error_count"]
        <= gates["maximum_request_error_count"],
        "maximum_temporal_leakage_count": summary["temporal_leakage_count"]
        <= gates["maximum_temporal_leakage_count"],
        "maximum_duplicate_event_count": duplicate_count
        <= gates["maximum_duplicate_event_count"],
    }
    args.output.mkdir(parents=True)
    (args.output / "classified-events.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in classified)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_result_sha256": sha256(result_path),
        "summary": summary,
        "checks": checks,
        "decision": "PRICE_ELIGIBILITY_PASS" if all(checks.values()) else "PRICE_ELIGIBILITY_FAIL",
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
