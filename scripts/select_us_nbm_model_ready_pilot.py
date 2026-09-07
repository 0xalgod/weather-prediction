#!/usr/bin/env python3
"""Select a metadata-only shared-date US pilot cohort and estimate request cost."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evenly_spaced_indices(item_count: int, selection_count: int) -> list[int]:
    if selection_count < 2 or item_count < selection_count:
        raise ValueError("not enough items for unique evenly spaced selection")
    indices = [
        round(index * (item_count - 1) / (selection_count - 1))
        for index in range(selection_count)
    ]
    if len(set(indices)) != selection_count:
        raise ValueError("rounded selection indices are not unique")
    return indices


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
    minimum_date = config["cohort"]["minimum_target_date"]
    maximum_date = config["cohort"]["maximum_target_date"]

    # Selection uses identity metadata only. Outcome/bucket content is read only after IDs freeze.
    candidates = defaultdict(lambda: defaultdict(list))
    row_by_event_id = {}
    for row in inventory["rows"]:
        identity = {
            "event_id": row["event_id"],
            "city": row["city"],
            "target_date": row["target_date"],
            "resolution_source": row["resolution_source"],
        }
        if identity["city"] in cities and minimum_date <= identity["target_date"] <= maximum_date:
            candidates[identity["target_date"]][identity["city"]].append(identity)
            row_by_event_id[identity["event_id"]] = row

    eligible_dates = sorted(
        target_date
        for target_date, by_city in candidates.items()
        if set(by_city) == cities and all(len(rows) == 1 for rows in by_city.values())
    )
    count = config["cohort"]["selected_date_count"]
    indices = evenly_spaced_indices(len(eligible_dates), count)
    selected_dates = [eligible_dates[index] for index in indices]
    identities = [
        candidates[target_date][city][0]
        for target_date in selected_dates
        for city in config["cohort"]["cities"]
    ]
    selected_ids = {row["event_id"] for row in identities}
    selected_events = [row_by_event_id[event_id] for event_id in selected_ids]
    selected_events.sort(key=lambda row: (row["target_date"], row["city"]))

    nbm_probe_path = Path(config["source_nbm_probe"])
    nbm_probe = json.loads(nbm_probe_path.read_text())
    max_object_bytes = max(row["retrieval"]["byte_count"] for row in nbm_probe["retrievals"])
    market_request_count = sum(len(row["buckets"]) for row in selected_events)
    duplicate_count = len(identities) - len(
        {(row["city"], row["target_date"]) for row in identities}
    )
    summary = {
        "eligible_shared_date_count": len(eligible_dates),
        "selected_date_count": len(selected_dates),
        "selected_event_count": len(selected_events),
        "city_count": len({row["city"] for row in identities}),
        "duplicate_city_date_count": duplicate_count,
        "selected_bucket_and_market_request_count": market_request_count,
        "nbm_full_object_count": len(selected_dates),
        "max_observed_nbm_object_bytes": max_object_bytes,
        "conservative_nbm_transfer_bytes": max_object_bytes * len(selected_dates),
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_selected_date_count": summary["selected_date_count"]
        == gates["exact_selected_date_count"],
        "exact_selected_event_count": summary["selected_event_count"]
        == gates["exact_selected_event_count"],
        "exact_city_count": summary["city_count"] == gates["exact_city_count"],
        "maximum_duplicate_city_date_count": duplicate_count
        <= gates["maximum_duplicate_city_date_count"],
        "maximum_nbm_full_object_transfer_bytes": summary["conservative_nbm_transfer_bytes"]
        <= gates["maximum_nbm_full_object_transfer_bytes"],
    }
    args.output.mkdir(parents=True)
    (args.output / "selected-events.json").write_text(
        json.dumps(selected_events, indent=2, sort_keys=True) + "\n"
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "stage": "metadata_selection_and_cost",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_inventory_sha256": sha256(inventory_path),
        "source_nbm_probe_sha256": sha256(nbm_probe_path),
        "selected_dates": selected_dates,
        "selected_event_ids": sorted(selected_ids, key=int),
        "summary": summary,
        "checks": checks,
        "decision": "COHORT_SELECTION_PASS" if all(checks.values()) else "COHORT_SELECTION_FAIL",
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
