#!/usr/bin/env python3
"""Replay frozen US price histories at the preregistered 24-hour cutoff."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from weather_quant.ingestion.multicity_price_horizon import event_horizon_coverage
from weather_quant.ingestion.polymarket_price_history import parse_utc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    events_path = Path(config["source_selected_events"])
    if sha256_path(events_path) != config["source_selected_events_sha256"]:
        raise ValueError("selected-event checksum mismatch")
    events = json.loads(events_path.read_text())

    price_run = Path(config["source_price_run"])
    histories = {}
    for path in sorted((price_run / "responses").glob("token-*.json")):
        response = json.loads(path.read_text())
        if response["http_status"] == 200:
            histories[str(response["yes_token_id"])] = json.loads(response["body_text"])[
                "history"
            ]

    nbm_result_path = Path(config["source_nbm_run"]) / "result.json"
    nbm_result = json.loads(nbm_result_path.read_text())
    publication_by_target = {}
    for item in nbm_result["retrievals"]:
        run_date = item["record"]["run_date"]
        target = (datetime.strptime(run_date, "%Y%m%d").date() + timedelta(days=1)).isoformat()
        publication_by_target[target] = item["retrieval"]["http_last_modified"]

    contract = config["replay_contract"]
    rows = []
    for event in events:
        coverage = event_horizon_coverage(
            event,
            histories,
            [contract["horizon_hours_before_end"]],
            contract["maximum_staleness_seconds"],
        )[0]
        publication = publication_by_target[event["target_date"]]
        cutoff = parse_utc(coverage["cutoff_utc"])
        publication_time = parsedate_to_datetime(publication)
        nbm_admissible = publication_time <= cutoff
        eligibility = (
            "PRICE_ELIGIBLE_24H"
            if coverage["usable_full_vector"] and nbm_admissible
            else "NO_TRADE_PRICE"
            if not coverage["usable_full_vector"]
            else "NO_TRADE_NBM_NOT_PUBLISHED"
        )
        rows.append(
            {
                **coverage,
                "nbm_http_last_modified": publication,
                "nbm_publication_admissible": nbm_admissible,
                "eligibility": eligibility,
            }
        )

    eligible = [row for row in rows if row["eligibility"] == "PRICE_ELIGIBLE_24H"]
    city_counts = Counter(row["city"] for row in eligible)
    duplicate_count = len(rows) - len({str(row["event_id"]) for row in rows})
    leakage = sum(
        point["timestamp"] > int(parse_utc(row["cutoff_utc"]).timestamp())
        for row in rows
        for point in row["points"]
    )
    late_nbm = sum(not row["nbm_publication_admissible"] for row in rows)
    summary = {
        "source_event_count": len(events),
        "eligible_event_count": len(eligible),
        "eligible_event_rate": len(eligible) / len(events),
        "no_trade_event_count": len(rows) - len(eligible),
        "eligible_target_date_count": len({row["target_date"] for row in eligible}),
        "city_count": len(city_counts),
        "minimum_eligible_event_count_per_city": min(city_counts.values(), default=0),
        "eligible_event_count_by_city": dict(sorted(city_counts.items())),
        "temporal_leakage_count": leakage,
        "nbm_publication_after_cutoff_count": late_nbm,
        "duplicate_event_count": duplicate_count,
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_source_event_count": len(events) == gates["exact_source_event_count"],
        "minimum_eligible_event_count": len(eligible) >= gates["minimum_eligible_event_count"],
        "minimum_eligible_event_rate": summary["eligible_event_rate"]
        >= gates["minimum_eligible_event_rate"],
        "minimum_eligible_target_date_count": summary["eligible_target_date_count"]
        >= gates["minimum_eligible_target_date_count"],
        "minimum_eligible_event_count_per_city": summary[
            "minimum_eligible_event_count_per_city"
        ]
        >= gates["minimum_eligible_event_count_per_city"],
        "exact_city_count": len(city_counts) == gates["exact_city_count"],
        "maximum_temporal_leakage_count": leakage
        <= gates["maximum_temporal_leakage_count"],
        "maximum_nbm_publication_after_cutoff_count": late_nbm
        <= gates["maximum_nbm_publication_after_cutoff_count"],
        "maximum_duplicate_event_count": duplicate_count
        <= gates["maximum_duplicate_event_count"],
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "selected_events_sha256": sha256_path(events_path),
        "source_price_result_sha256": sha256_path(price_run / "result.json"),
        "source_nbm_result_sha256": sha256_path(nbm_result_path),
        "summary": summary,
        "checks": checks,
        "decision": (
            "PRICE_24H_COVERAGE_PASS"
            if all(checks.values())
            else "PRICE_24H_COVERAGE_FAIL"
        ),
        "boundary": config["boundary"],
    }
    args.output.mkdir(parents=True)
    (args.output / "event-coverage.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
