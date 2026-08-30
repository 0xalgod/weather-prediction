#!/usr/bin/env python3
"""Capture a deterministic active-event sample from the public CLOB /book endpoint."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.ingestion.polymarket_markets import normalize_highest_temperature_event, write_raw_envelope
from weather_quant.ingestion.polymarket_orderbook import (
    fetch_book_envelope,
    fetch_tick_size_envelope,
    normalize_book,
    normalize_tick_size,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gamma-raw-directory", type=Path, required=True)
    parser.add_argument("--gamma-summary", type=Path, required=True)
    parser.add_argument("--event-sample-size", type=int, default=3)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists() or args.raw_directory.exists():
        raise FileExistsError("snapshot outputs must be new immutable paths")
    gamma_summary = json.loads(args.gamma_summary.read_text(encoding="utf-8"))
    as_of = datetime.fromisoformat(gamma_summary["started_at_utc"].replace("Z", "+00:00"))
    normalized = []
    for event, _ in iter_raw_events(args.gamma_raw_directory):
        item = normalize_highest_temperature_event(event, as_of)
        if item.event["temporally_relevant"] and item.markets and all(m["eligible_for_book_collection"] for m in item.markets):
            normalized.append(item)
    selected = sorted(normalized, key=lambda x: (x.event["end_at"], x.event["event_id"]), reverse=True)[: args.event_sample_size]
    if len(selected) != args.event_sample_size:
        raise ValueError("insufficient eligible active events")

    token_context = {}
    for event in selected:
        markets = {market["market_id"]: market for market in event.markets}
        for outcome in event.outcomes:
            market = markets[outcome["market_id"]]
            token_context[outcome["token_id"]] = {
                "event_id": event.event["event_id"], "city_label": event.event["city_label"],
                "end_at": event.event["end_at"], "market_id": outcome["market_id"],
                "outcome_label": outcome["outcome_label"], "tick_size": str(market["minimum_tick_size"]),
            }

    envelopes = {}
    tick_envelopes = {}
    errors = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {}
        for token in token_context:
            futures[executor.submit(fetch_book_envelope, token)] = (token, "book")
            futures[executor.submit(fetch_tick_size_envelope, token)] = (token, "tick_size")
        for future in as_completed(futures):
            token, kind = futures[future]
            try:
                if kind == "book":
                    envelopes[token] = future.result()
                else:
                    tick_envelopes[token] = future.result()
            except Exception as error:
                errors[f"{token}|{kind}"] = f"{type(error).__name__}: {error}"

    snapshots = []
    for token, envelope in sorted(envelopes.items()):
        if token not in tick_envelopes:
            continue
        write_raw_envelope(envelope, args.raw_directory / f"token-{token}.json")
        write_raw_envelope(tick_envelopes[token], args.raw_directory / f"token-{token}-tick-size.json")
        book = normalize_book(envelope, token)
        tick = normalize_tick_size(tick_envelopes[token])
        tick_violations = sum(Decimal(level["price"]) % tick != 0 for side in (book["bids"], book["asks"]) for level in side)
        requested = datetime.fromisoformat(book["requested_at_utc"].replace("Z", "+00:00"))
        received = datetime.fromisoformat(book["received_at_utc"].replace("Z", "+00:00"))
        snapshots.append({
            **token_context[token], "gamma_tick_size": token_context[token]["tick_size"],
            "dynamic_tick_size": str(tick), "asset_id": token, "market": book["market"],
            "exchange_timestamp_ms": book["exchange_timestamp_ms"], "book_hash": book["book_hash"],
            "content_sha256": book["content_sha256"], "requested_at_utc": book["requested_at_utc"],
            "received_at_utc": book["received_at_utc"], "request_latency_ms": (received - requested).total_seconds() * 1000,
            "bid_level_count": len(book["bids"]), "ask_level_count": len(book["asks"]),
            "bids": book["bids"], "asks": book["asks"],
            "best_bid": book["best_bid"], "best_ask": book["best_ask"], "spread": book["spread"],
            "quality": book["quality"], "tick_violation_count": tick_violations,
        })

    output = {
        "schema_version": "0.1.0", "gamma_run_id": gamma_summary["run_id"],
        "selected_events": [{"event_id": x.event["event_id"], "city_label": x.event["city_label"], "end_at": x.event["end_at"]} for x in selected],
        "requested_token_count": len(token_context), "successful_snapshot_count": len(snapshots),
        "failed_snapshot_count": len(token_context) - len(snapshots), "request_error_count": len(errors), "errors": errors,
        "quality_counts": dict(sorted(Counter(x["quality"] for x in snapshots).items())),
        "tick_violation_count": sum(x["tick_violation_count"] for x in snapshots),
        "snapshots": snapshots, "raw_directory": str(args.raw_directory),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("selected_events", "requested_token_count", "successful_snapshot_count", "failed_snapshot_count", "quality_counts", "tick_violation_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
