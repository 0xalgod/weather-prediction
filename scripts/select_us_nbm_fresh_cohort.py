#!/usr/bin/env python3
"""Select a disjoint metadata-only cohort for the 13Z versus 07Z comparison."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path
from scripts.select_us_nbm_model_ready_pilot import evenly_spaced_indices


def retrieval_sizes(result: dict) -> list[int]:
    return [
        row["retrieval"]["byte_count"]
        for row in result["retrievals"]
        if row.get("retrieval") is not None
    ]


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
    cities = set(config["cohort"]["cities"])
    excluded = set(config["cohort"]["excluded_dates"])
    minimum = config["cohort"]["minimum_target_date"]
    maximum = config["cohort"]["maximum_target_date"]

    candidates = defaultdict(lambda: defaultdict(list))
    rows_by_id = {}
    for row in inventory["rows"]:
        identity = {
            "event_id": str(row["event_id"]),
            "city": row["city"],
            "target_date": row["target_date"],
            "resolution_source": row["resolution_source"],
        }
        if (
            identity["city"] in cities
            and minimum <= identity["target_date"] <= maximum
            and identity["target_date"] not in excluded
        ):
            candidates[identity["target_date"]][identity["city"]].append(identity)
            rows_by_id[identity["event_id"]] = row
    eligible_dates = sorted(
        target
        for target, by_city in candidates.items()
        if set(by_city) == cities and all(len(values) == 1 for values in by_city.values())
    )
    selection_count = config["cohort"]["selected_date_count"]
    indices = evenly_spaced_indices(len(eligible_dates), selection_count)
    selected_dates = [eligible_dates[index] for index in indices]
    identities = [
        candidates[target][city][0]
        for target in selected_dates
        for city in config["cohort"]["cities"]
    ]
    selected_events = [rows_by_id[row["event_id"]] for row in identities]
    selected_events.sort(key=lambda row: (row["target_date"], row["city"]))

    report_13_path = Path(config["source_13z_probe"])
    report_13 = json.loads(report_13_path.read_text())
    result_13_path = Path(report_13["result_path"])
    result_13 = json.loads(result_13_path.read_text())
    result_07_path = Path(config["source_07z_probe_result"])
    result_07 = json.loads(result_07_path.read_text())
    max_object_bytes = max(retrieval_sizes(result_07) + retrieval_sizes(result_13))
    conservative_transfer = max_object_bytes * selection_count * 2
    city_counts = Counter(row["city"] for row in identities)
    duplicate_count = len(identities) - len(
        {(row["city"], row["target_date"]) for row in identities}
    )
    overlap_count = len(set(selected_dates) & excluded)
    summary = {
        "remaining_eligible_shared_date_count": len(eligible_dates),
        "selected_date_count": len(selected_dates),
        "selected_event_count": len(selected_events),
        "city_count": len(city_counts),
        "minimum_events_per_city": min(city_counts.values()),
        "maximum_events_per_city": max(city_counts.values()),
        "excluded_date_overlap_count": overlap_count,
        "duplicate_city_date_count": duplicate_count,
        "market_token_request_count": sum(len(row["buckets"]) for row in selected_events),
        "planned_full_nbm_object_count": selection_count * 2,
        "maximum_observed_probe_object_bytes": max_object_bytes,
        "conservative_nbm_transfer_bytes": conservative_transfer,
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_selected_date_count": len(selected_dates) == gates["exact_selected_date_count"],
        "exact_selected_event_count": len(selected_events) == gates["exact_selected_event_count"],
        "exact_city_count": len(city_counts) == gates["exact_city_count"],
        "exact_events_per_city": min(city_counts.values())
        == max(city_counts.values())
        == gates["exact_events_per_city"],
        "maximum_excluded_date_overlap_count": overlap_count
        <= gates["maximum_excluded_date_overlap_count"],
        "maximum_duplicate_city_date_count": duplicate_count
        <= gates["maximum_duplicate_city_date_count"],
        "maximum_conservative_nbm_transfer_bytes": conservative_transfer
        <= gates["maximum_conservative_nbm_transfer_bytes"],
    }
    args.output.mkdir(parents=True)
    (args.output / "selected-events.json").write_text(
        json.dumps(selected_events, indent=2, sort_keys=True) + "\n"
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "source_inventory_sha256": sha256_path(inventory_path),
        "source_07z_probe_sha256": sha256_path(result_07_path),
        "source_13z_probe_report_sha256": sha256_path(report_13_path),
        "source_13z_probe_result_sha256": sha256_path(result_13_path),
        "selected_dates": selected_dates,
        "summary": summary,
        "checks": checks,
        "decision": (
            "FRESH_COHORT_SELECTION_PASS"
            if all(checks.values())
            else "FRESH_COHORT_SELECTION_FAIL"
        ),
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
