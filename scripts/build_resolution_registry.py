#!/usr/bin/env python3
"""Build candidate resolution-registry JSONL from fixed reconciliation evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from weather_quant.normalization.manual_reconciliation import parse_resolution_rule
from weather_quant.normalization.resolution_rules import (
    ResolutionRegistryError,
    build_bucket_records,
    rule_sha256,
    validate_resolution_record,
)


DISPOSITIONS = {
    "RECONCILED": ("CANDIDATE_STATION_UNVERIFIED", ["STATION_TIMEZONE_UNVERIFIED"]),
    "NO_TRADE_MISSING_RESOLUTION_SOURCE": ("NO_TRADE_MISSING_RESOLUTION_SOURCE", ["MISSING_RESOLUTION_SOURCE"]),
    "NON_TERMINAL_OR_CANCELLED": ("NO_TRADE_NON_TERMINAL_OR_CANCELLED", ["NO_EXACT_TERMINAL_WINNER"]),
    "OUTCOME_SOURCE_MISMATCH_NO_TRADE": ("NO_TRADE_OUTCOME_SOURCE_MISMATCH", ["OUTCOME_SOURCE_MISMATCH"]),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--station-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"output exists: {args.output}")
    reconciliation = json.loads(args.reconciliation.read_text(encoding="utf-8"))
    station_config = json.loads(args.station_config.read_text(encoding="utf-8"))
    raw_directory = Path(reconciliation["raw_manifest"]).parent
    manifest = json.loads((raw_directory / "manifest.json").read_text(encoding="utf-8"))
    files = {(item["event_id"], item["kind"]): item for item in manifest["files"]}
    records = []

    for audit in reconciliation["records"]:
        event_id = audit["event_id"]
        gamma = json.loads((raw_directory / f"event-{event_id}-gamma.json").read_text(encoding="utf-8"))
        source_url = gamma.get("resolutionSource")
        markets = gamma.get("markets", [])
        description = str(markets[0].get("description") or gamma.get("description") or "") if markets else str(gamma.get("description") or "")
        parsed_rule = parse_resolution_rule(description, source_url)
        disposition, exclusions = DISPOSITIONS[audit["disposition"]]
        rule_hash = rule_sha256(description) if description else None
        station_code = parsed_rule.get("station_code")
        timezone = station_config["stations"].get(station_code)
        if disposition == "CANDIDATE_STATION_UNVERIFIED" and not timezone:
            raise ResolutionRegistryError(f"missing candidate timezone for retained station {station_code}")
        try:
            buckets = build_bucket_records(markets, parsed_rule["unit"]) if parsed_rule.get("unit") else []
        except ResolutionRegistryError:
            if disposition == "CANDIDATE_STATION_UNVERIFIED":
                raise
            buckets = []
            exclusions = sorted(set(exclusions + ["INCOMPLETE_BUCKET_IDENTIFIERS"]))

        market_date = datetime.strptime(parsed_rule["rule_date"], "%d %b '%y").date().isoformat() if parsed_rule.get("rule_date") else gamma["endDate"][:10]
        record: Dict[str, Any] = {
            "schema_version": "0.1.0",
            "registry_record_id": f"polymarket-event-{event_id}-rule-{rule_hash[:12] if rule_hash else 'missing'}",
            "event_id": event_id,
            "event_slug": gamma["slug"],
            "city_label": audit["title"].split("Highest temperature in ", 1)[1].rsplit(" on ", 1)[0],
            "market_date_local": market_date,
            "disposition": disposition,
            "exclusion_reasons": exclusions,
            "rule": {
                "provider": "Wunderground" if source_url else None,
                "source_url": source_url,
                "station_code": station_code,
                "station_name": parsed_rule.get("station_name"),
                "timezone": timezone,
                "temperature_unit": parsed_rule.get("unit"),
                "temperature_precision": 1 if parsed_rule.get("unit") else None,
                "rounding_mode": "SOURCE_REPORTED_WHOLE_DEGREE" if parsed_rule.get("unit") else None,
                "observation_window": {"basis": "LOCAL_CALENDAR_DAY", "start_local": "00:00:00", "end_local": "23:59:59.999999", "end_inclusive": True} if parsed_rule.get("unit") else None,
                "rule_text": description or None,
                "rule_text_sha256": rule_hash,
                "rule_version": f"sha256:{rule_hash}" if rule_hash else None,
            },
            "buckets": buckets,
            "provenance": {
                "gamma_observed_at_utc": manifest["retrieved_at_utc"],
                "resolution_observed_at_utc": manifest["retrieved_at_utc"] if (event_id, "resolution_page") in files else None,
                "gamma_content_sha256": files[(event_id, "gamma")]["sha256"],
                "resolution_content_sha256": files.get((event_id, "resolution_page"), {}).get("sha256"),
                "parser_version": "0.1.0",
            },
        }
        validate_resolution_record(record)
        records.append(record)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        for record in records:
            destination.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "record_count": len(records),
        "station_unverified_candidate_count": sum(item["disposition"] == "CANDIDATE_STATION_UNVERIFIED" for item in records),
        "hard_no_trade_count": sum(item["disposition"].startswith("NO_TRADE") for item in records),
        "bucket_count": sum(len(item["buckets"]) for item in records),
        "station_count": len({item["rule"]["station_code"] for item in records if item["rule"]["station_code"]}),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
