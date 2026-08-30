#!/usr/bin/env python3
"""Replay a stability capture and report mismatch/reconnect concentration."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from weather_quant.ingestion.polymarket_websocket import (
    RecoveryState,
    apply_events,
    decode_market_frame,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_summary = json.loads(args.summary.read_text(encoding="utf-8"))
    assets = frozenset(item["asset_id"] for item in source_summary["selection"])
    city_by_asset = {
        item["asset_id"]: item["city_label"] for item in source_summary["selection"]
    }
    connections = []
    mismatch_by_asset: Counter[str] = Counter()
    mismatch_by_city: Counter[str] = Counter()
    replay_total = 0

    for path in sorted(args.run_directory.glob("connection-*.jsonl")):
        state = RecoveryState(assets)
        frame_count = 0
        first_received = None
        last_received = None
        first_mismatch = None
        last_mismatch = None
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            frame_count += 1
            first_received = first_received or record["received_at_utc"]
            last_received = record["received_at_utc"]
            events = decode_market_frame(record["raw"])
            before = state.advertised_top_mismatch_count
            apply_events(state, events)
            difference = state.advertised_top_mismatch_count - before
            if difference:
                first_mismatch = first_mismatch or record["received_at_utc"]
                last_mismatch = record["received_at_utc"]
                replay_total += difference
                for event in events:
                    for change in event.get("price_changes", []):
                        asset_id = str(change.get("asset_id") or "")
                        if asset_id in assets:
                            mismatch_by_asset[asset_id] += 1
                            mismatch_by_city[city_by_asset[asset_id]] += 1
        connections.append(
            {
                "connection_file": path.name,
                "frame_count": frame_count,
                "first_received_at_utc": first_received,
                "last_received_at_utc": last_received,
                "ready_at_end": state.ready,
                "full_book_count": state.event_counts.get("book", 0),
                "replayed_mismatch_count": state.advertised_top_mismatch_count,
                "first_mismatch_at_utc": first_mismatch,
                "last_mismatch_at_utc": last_mismatch,
            }
        )

    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "analysis": "phase3-host-sleep-contaminated-replay",
        "source_run": args.run_directory.name,
        "source_summary_snapshot": {
            "started_at_utc": source_summary["started_at_utc"],
            "updated_at_utc": source_summary["updated_at_utc"],
            "elapsed_seconds": source_summary["elapsed_seconds"],
            "status_at_interrupt": "HOST_SLEEP_CONTAMINATED_INTERRUPTED",
            "metrics": source_summary["metrics"],
            "derived": source_summary["derived"],
        },
        "replay": {
            "connection_count": len(connections),
            "frame_count": sum(item["frame_count"] for item in connections),
            "advertised_top_mismatch_count": replay_total,
            "mismatch_by_asset": dict(mismatch_by_asset.most_common()),
            "mismatch_by_city": dict(mismatch_by_city.most_common()),
            "connections": connections,
        },
        "host_sleep_evidence": {
            "source": "macOS pmset -g log observed 2026-08-31 Europe/Istanbul",
            "classification": "CONFIRMED",
            "notable_intervals_local": [
                "2026-08-30 14:49:39–15:07:55 Clamshell/Maintenance Sleep",
                "2026-08-30 17:32:38–18:37:57 repeated Idle/Maintenance Sleep",
                "2026-08-31 00:25:56–00:54:59 repeated Idle/Maintenance Sleep",
            ],
        },
        "decision": "INVALID_FOR_STABILITY_GATE_VALID_FOR_FAILURE_DIAGNOSIS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "replay": artifact["replay"]}, indent=2))


if __name__ == "__main__":
    main()
