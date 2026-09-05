#!/usr/bin/env python3
"""Read-only discovery of a preregistered upcoming exact-rule KORD event."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.ingestion.kord_candidate import audit_upcoming_kord_candidate
from weather_quant.ingestion.polymarket_markets import GammaDiscoveryClient, write_raw_envelope


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=500)
    args = parser.parse_args()
    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = args.raw_root / f"run={run_id}"
    client = GammaDiscoveryClient()
    audits = []
    source_event_count = 0
    event_ids = []
    page_count = 0
    city_counts = Counter()
    for page_count, envelope in enumerate(
        client.iter_event_envelopes(
            tag_slug="highest-temperature", closed=False, page_size=args.page_size
        ),
        start=1,
    ):
        write_raw_envelope(
            envelope,
            raw_dir / f"page-{page_count:05d}-{envelope['content_sha256'][:12]}.json",
        )
        for event in envelope["payload"]["events"]:
            source_event_count += 1
            event_ids.append(str(event.get("id") or ""))
            title = str(event.get("title") or "")
            city = title.removeprefix("Highest temperature in ").split(" on ", 1)[0]
            city_counts[city] += 1
            if title.startswith("Highest temperature in Chicago on "):
                audits.append(audit_upcoming_kord_candidate(event, started))

    qualified = sorted(
        (record for record in audits if record["qualified"]),
        key=lambda record: (record["end_at"], int(record["event_id"])),
    )
    check_counts = {
        check: sum(record["checks"][check] for record in audits)
        for check in (audits[0]["checks"] if audits else [])
    }
    artifact = {
        "schema_version": "0.1.0",
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "discovery": "upcoming-supported-primary-kord-event",
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "query": {"tag_slug": "highest-temperature", "closed": False},
        "page_count": page_count,
        "source_event_count": source_event_count,
        "duplicate_event_count": sum(
            count - 1 for count in Counter(event_ids).values() if count > 1
        ),
        "unique_city_count": len(city_counts),
        "chicago_event_count": len(audits),
        "chicago_check_pass_counts": check_counts,
        "qualified_event_count": len(qualified),
        "selection_rule": "earliest end_at then numeric event_id",
        "selected_event": qualified[0] if qualified else None,
        "availability_status": "AVAILABLE" if qualified else "NOT_AVAILABLE",
        "chicago_audits": audits,
        "raw_directory": str(raw_dir),
        "safety": "PUBLIC_GET_ONLY_NO_ORDER_NO_CREDENTIAL_NO_BACKGROUND_COLLECTOR",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
