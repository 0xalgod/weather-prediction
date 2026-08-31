#!/usr/bin/env python3
"""Audit a fixed Wunderground/current-page cohort against terminal buckets."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.market_model.settlement_audit import (
    classify_settlement_record,
    wilson_interval,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-sample", type=Path, required=True)
    parser.add_argument("--sentinel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sentinel_record(document: dict) -> dict:
    market = document["polymarket"]
    match = market["matches"][0]
    return {
        "event_id": match["event_id"],
        "title": match["title"],
        "identity_match": document["checks"]["wunderground_identity"],
        "terminal_status": "EXACT_TERMINAL_WINNER"
        if market["terminal_winner"]
        else "NO_EXACT_TERMINAL_WINNER",
        "terminal_winner_bucket": market["terminal_winner"],
        "observed_high_display": {
            "value": document["wunderground"]["daily_high"],
            "unit": document["wunderground"]["temperature_unit"],
        },
        "rule": {"station_code": document["wunderground"]["station_code"]},
        "disposition": "HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT",
    }


def summarize(records: list[dict]) -> dict:
    eligible = [record for record in records if record["eligible"]]
    matches = [record for record in eligible if record["comparison"] == "MATCH"]
    divergences = [record for record in eligible if record["comparison"] == "MISMATCH"]
    unresolved = [
        record
        for record in eligible
        if record["comparison"] not in {"MATCH", "MISMATCH"}
    ]
    interval = wilson_interval(len(divergences), len(eligible)) if eligible else (None, None)
    return {
        "registered_record_count": len(records),
        "eligible_event_count": len(eligible),
        "eligible_city_count": len({record["city"] for record in eligible}),
        "match_event_count": len(matches),
        "match_city_count": len({record["city"] for record in matches}),
        "diverged_event_count": len(divergences),
        "diverged_city_count": len({record["city"] for record in divergences}),
        "ineligible_event_count": sum(not record["eligible"] for record in records),
        "unresolved_eligible_count": len(unresolved),
        "divergence_rate": len(divergences) / len(eligible) if eligible else None,
        "divergence_wilson_95_low": interval[0],
        "divergence_wilson_95_high": interval[1],
        "comparison_counts": dict(Counter(record["comparison"] for record in records)),
        "diverged_event_ids": [record["event_id"] for record in divergences],
        "all_divergences_quarantined": all(
            not record["current_page_bucket_consistent"]
            and not record["temperature_label_eligible"]
            for record in divergences
        ),
        "market_terminal_label_available_count": sum(
            record["market_terminal_label_available"] for record in records
        ),
        "temperature_label_eligible_count": sum(
            record["temperature_label_eligible"] for record in records
        ),
    }


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"immutable artifact exists: {args.output}")
    fixed_document = json.loads(args.fixed_sample.read_text(encoding="utf-8"))
    sentinel_document = json.loads(args.sentinel.read_text(encoding="utf-8"))
    fixed_records = [
        {**classify_settlement_record(record), "cohort_role": "FIXED_STRATIFIED_SAMPLE"}
        for record in fixed_document["records"]
    ]
    sentinel = {
        **classify_settlement_record(sentinel_record(sentinel_document)),
        "cohort_role": "ANOMALY_SENTINEL",
    }
    all_records = [*fixed_records, sentinel]
    fixed_summary = summarize(fixed_records)
    combined_summary = summarize(all_records)
    gate_passed = (
        combined_summary["match_event_count"] >= 10
        and combined_summary["match_city_count"] >= 3
        and combined_summary["unresolved_eligible_count"] == 0
        and combined_summary["all_divergences_quarantined"]
    )
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "audit": "fixed-wunderground-current-page-vs-terminal-settlement",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "fixed_sample_path": str(args.fixed_sample),
            "fixed_sample_sha256": sha256(args.fixed_sample),
            "fixed_sample_retrieved_at_utc": fixed_document["retrieved_at_utc"],
            "sentinel_path": str(args.sentinel),
            "sentinel_sha256": sha256(args.sentinel),
            "sentinel_generated_at_utc": sentinel_document["generated_at_utc"],
        },
        "pre_registered_gate": {
            "match_event_count_minimum": 10,
            "match_city_count_minimum": 3,
            "unresolved_eligible_count": 0,
            "all_divergences_quarantined": True,
        },
        "fixed_sample_summary": fixed_summary,
        "combined_with_sentinel_summary": combined_summary,
        "sample_observation_settlement_gate_passed": gate_passed,
        "interpretation_limit": (
            "A match is current-page/terminal-bucket consistency, not proof that the page "
            "was identical at the historical freeze timestamp."
        ),
        "records": all_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "gate_passed": gate_passed,
                "fixed_sample": fixed_summary,
                "combined": combined_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
