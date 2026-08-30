#!/usr/bin/env python3
"""Run a bounded public WebSocket heartbeat, delta-replay, and REST-anchor shakeout."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from websockets.asyncio.client import connect

from weather_quant.ingestion.polymarket_orderbook import fetch_book_envelope
from weather_quant.ingestion.polymarket_websocket import (
    RecoveryState,
    apply_events,
    book_top,
    decode_market_frame,
    raw_event_record,
)

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rest-coverage", type=Path, required=True)
    parser.add_argument("--asset-count", type=int, default=12)
    parser.add_argument("--duration-seconds", type=float, default=35.0)
    parser.add_argument("--initial-timeout-seconds", type=float, default=15.0)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def select_liquid_assets(path: Path, asset_count: int) -> list[dict[str, Any]]:
    coverage = json.loads(path.read_text(encoding="utf-8"))
    candidates = [item for item in coverage["snapshots"] if item["quality"] == "TWO_SIDED_BOOK"]
    candidates.sort(
        key=lambda item: (
            float(item["spread"]),
            -(item["bid_level_count"] + item["ask_level_count"]),
            item["asset_id"],
        )
    )
    selected = candidates[:asset_count]
    if len(selected) != asset_count:
        raise ValueError("insufficient two-sided assets")
    return [
        {
            "asset_id": item["asset_id"],
            "event_id": item["event_id"],
            "market_id": item["market_id"],
            "city_label": item["city_label"],
            "outcome_label": item["outcome_label"],
            "selection_spread": item["spread"],
        }
        for item in selected
    ]


async def capture(
    assets: list[str], raw_path: Path, duration: float, initial_timeout: float
) -> tuple[RecoveryState, dict[str, Any]]:
    state = RecoveryState(frozenset(assets))
    started = monotonic()
    deadline = started + duration
    next_ping = started + 10.0
    sequence = 0
    heartbeat_sent = 0
    with raw_path.open("x", encoding="utf-8") as output:
        async with connect(WS_URL, ping_interval=None, close_timeout=5) as websocket:
            await websocket.send(json.dumps({"assets_ids": assets, "type": "market"}))
            while monotonic() < deadline:
                now = monotonic()
                if not state.ready and now - started >= initial_timeout:
                    raise TimeoutError("initial full-book coverage deadline exceeded")
                wait_seconds = min(deadline, next_ping) - now
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=max(wait_seconds, 0.001))
                except asyncio.TimeoutError:
                    if monotonic() >= next_ping and monotonic() < deadline:
                        await websocket.send("PING")
                        heartbeat_sent += 1
                        next_ping += 10.0
                    continue
                if not isinstance(raw, str):
                    raise TypeError("binary market frame is unsupported")
                sequence += 1
                record = raw_event_record(raw, "shakeout-connection-1", sequence, utc_iso())
                output.write(json.dumps(record, sort_keys=True) + "\n")
                apply_events(state, decode_market_frame(raw))
    metrics = {
        "duration_seconds": monotonic() - started,
        "frame_count": sequence,
        "heartbeat_sent_count": heartbeat_sent,
        "pong_received_count": state.event_counts.get("pong", 0),
        "full_book_count": len(state.books),
        "delta_event_count": state.event_counts.get("price_change", 0),
        "applied_change_count": state.applied_change_count,
        "tick_change_count": state.event_counts.get("tick_size_change", 0),
        "delta_before_book_count": state.delta_before_book_count,
        "advertised_top_mismatch_count": state.advertised_top_mismatch_count,
        "event_counts": state.event_counts,
    }
    return state, metrics


async def rest_anchor(
    assets: list[str], state: RecoveryState, raw_directory: Path
) -> list[dict[str, Any]]:
    envelopes = await asyncio.gather(
        *(asyncio.to_thread(fetch_book_envelope, asset_id) for asset_id in assets)
    )
    comparisons = []
    for asset_id, envelope in zip(assets, envelopes):
        raw_path = raw_directory / f"rest-anchor-{asset_id}.json"
        raw_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ws_book = state.books[asset_id]
        rest_book = envelope["payload"]
        comparisons.append(
            {
                "asset_id": asset_id,
                "websocket_hash": ws_book.get("hash"),
                "rest_hash": rest_book.get("hash"),
                "hash_match": ws_book.get("hash") == rest_book.get("hash"),
                "websocket_top": book_top(ws_book),
                "rest_top": book_top(rest_book),
                "top_match": book_top(ws_book) == book_top(rest_book),
                "rest_requested_at_utc": envelope["requested_at_utc"],
                "rest_received_at_utc": envelope["received_at_utc"],
            }
        )
    return comparisons


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists() or args.raw_directory.exists():
        raise FileExistsError("shakeout outputs must be new immutable paths")
    args.raw_directory.mkdir(parents=True)
    started_at = utc_iso()
    selection = select_liquid_assets(args.rest_coverage, args.asset_count)
    assets = [item["asset_id"] for item in selection]
    state, metrics = await capture(
        assets,
        args.raw_directory / "websocket.jsonl",
        args.duration_seconds,
        args.initial_timeout_seconds,
    )
    comparisons = await rest_anchor(assets, state, args.raw_directory)
    reconcile_count = sum(item["hash_match"] or item["top_match"] for item in comparisons)
    reconciliation_rate = reconcile_count / len(comparisons)
    accepted = (
        metrics["full_book_count"] == args.asset_count
        and metrics["heartbeat_sent_count"] >= 3
        and metrics["pong_received_count"] >= 2
        and metrics["applied_change_count"] >= 1
        and metrics["delta_before_book_count"] == 0
        and metrics["advertised_top_mismatch_count"] == 0
        and reconciliation_rate >= 0.90
    )
    return {
        "schema_version": "0.1.0",
        "started_at_utc": started_at,
        "finished_at_utc": utc_iso(),
        "websocket_url": WS_URL,
        "selection": selection,
        "acceptance_criteria": {
            "full_book_coverage": 1.0,
            "heartbeat_sent_min": 3,
            "pong_received_min": 2,
            "applied_price_change_min": 1,
            "delta_before_book_max": 0,
            "advertised_top_mismatch_max": 0,
            "rest_hash_or_top_match_rate_min": 0.90,
        },
        "metrics": metrics,
        "rest_reconciliation_count": reconcile_count,
        "rest_reconciliation_rate": reconciliation_rate,
        "comparisons": comparisons,
        "accepted": accepted,
        "raw_directory": str(args.raw_directory),
    }


def main() -> int:
    args = parse_args()
    result = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
