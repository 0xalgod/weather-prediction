#!/usr/bin/env python3
"""Collect and summarize public Polymarket highest-temperature events."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from weather_quant.ingestion.polymarket_markets import (
    DiscoveryError,
    GammaDiscoveryClient,
    normalize_highest_temperature_event,
    summarize_discovery,
    write_raw_envelope,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/polymarket_discovery.json"))
    parser.add_argument("--closed", choices=("true", "false"), default="false")
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/polymarket_gamma"))
    parser.add_argument("--summary-output", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"configuration must be an object: {path}")
    return payload


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    run_started = datetime.now(timezone.utc)
    run_id = run_started.strftime("%Y%m%dT%H%M%SZ")
    closed = args.closed == "true"
    raw_directory = args.raw_root / f"closed={str(closed).lower()}" / f"run={run_id}"

    client = GammaDiscoveryClient(
        base_url=str(config["gamma_base_url"]),
        user_agent=str(config["user_agent"]),
        timeout_seconds=float(config["request_timeout_seconds"]),
    )
    normalized_events = []
    event_ids: List[str] = []
    page_count = 0
    source_event_count = 0

    try:
        envelopes = client.iter_event_envelopes(
            tag_slug=str(config["primary_tag_slug"]),
            closed=closed,
            page_size=int(config["page_size"]),
            max_pages=int(config["max_pages_safety_limit"]),
        )
        for page_count, envelope in enumerate(envelopes, start=1):
            checksum = str(envelope["content_sha256"])
            destination = raw_directory / f"page-{page_count:05d}-{checksum[:12]}.json"
            write_raw_envelope(envelope, destination)
            events = envelope["payload"]["events"]
            source_event_count += len(events)
            for event in events:
                event_ids.append(str(event.get("id") or ""))
                normalized_events.append(
                    normalize_highest_temperature_event(event, as_of=run_started)
                )
    except (DiscoveryError, OSError, ValueError) as error:
        print(f"discovery failed: {error}", file=sys.stderr)
        return 1

    summary = summarize_discovery(normalized_events)
    exclusion_reasons = Counter(
        reason
        for event in normalized_events
        for exclusion in event.exclusions
        for reason in exclusion["reason_codes"]
    )
    event_end_times = [event.event["end_at"] for event in normalized_events]
    city_event_counts = Counter(event.event["city_label"] for event in normalized_events)
    duplicate_event_count = sum(count - 1 for count in Counter(event_ids).values() if count > 1)
    completed_at = datetime.now(timezone.utc)

    output = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "closed_query": closed,
        "tag_slug": config["primary_tag_slug"],
        "started_at_utc": run_started.isoformat().replace("+00:00", "Z"),
        "completed_at_utc": completed_at.isoformat().replace("+00:00", "Z"),
        "page_count": page_count,
        "source_event_count": source_event_count,
        "duplicate_event_count": duplicate_event_count,
        "earliest_event_end_at": min(event_end_times) if event_end_times else None,
        "latest_event_end_at": max(event_end_times) if event_end_times else None,
        "summary": summary,
        "exclusion_reason_counts": dict(sorted(exclusion_reasons.items())),
        "city_event_counts": dict(sorted(city_event_counts.items())),
        "raw_directory": str(raw_directory),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    if args.summary_output.exists():
        print(f"summary output already exists: {args.summary_output}", file=sys.stderr)
        return 1
    args.summary_output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
