#!/usr/bin/env python3
"""Capture public market books, force reconnect, and reconcile recovery with REST."""

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
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    return parser.parse_args()


def select_same_market_tokens(path: Path) -> list[dict[str, str]]:
    coverage = json.loads(path.read_text(encoding="utf-8"))
    by_market: dict[str, list[dict[str, str]]] = {}
    for snapshot in coverage["snapshots"]:
        by_market.setdefault(snapshot["market_id"], []).append(snapshot)
    candidates = [items for items in by_market.values() if len(items) >= 2]
    if not candidates:
        raise ValueError("no market has at least two tokens")
    chosen = sorted(
        candidates,
        key=lambda items: (items[0]["city_label"], items[0]["market_id"]),
    )[0]
    return [
        {
            "asset_id": item["asset_id"],
            "market_id": item["market_id"],
            "city_label": item["city_label"],
            "outcome_label": item["outcome_label"],
        }
        for item in sorted(chosen, key=lambda item: item["outcome_label"])[:2]
    ]


async def capture_connection(
    assets: list[str], connection_id: str, raw_path: Path, timeout_seconds: float
) -> dict[str, Any]:
    state = RecoveryState(frozenset(assets))
    started = monotonic()
    sequence = 0
    with raw_path.open("x", encoding="utf-8") as output:
        async with connect(WS_URL, ping_interval=None, close_timeout=5) as websocket:
            await websocket.send(json.dumps({"assets_ids": assets, "type": "market"}))
            while not state.ready:
                remaining = timeout_seconds - (monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError(f"{connection_id} did not receive all full books")
                raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
                if not isinstance(raw, str):
                    raise TypeError("binary market frame is unsupported")
                sequence += 1
                received_at = utc_iso()
                record = raw_event_record(raw, connection_id, sequence, received_at)
                output.write(json.dumps(record, sort_keys=True) + "\n")
                apply_events(state, decode_market_frame(raw))
    return {
        "connection_id": connection_id,
        "recovery_seconds": monotonic() - started,
        "frame_count": sequence,
        "full_book_count": len(state.books),
        "delta_before_book_count": state.delta_before_book_count,
        "event_counts": state.event_counts,
        "books": state.books,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists() or args.raw_directory.exists():
        raise FileExistsError("capture outputs must be new immutable paths")
    args.raw_directory.mkdir(parents=True)
    started_at = utc_iso()
    selection = select_same_market_tokens(args.rest_coverage)
    assets = [item["asset_id"] for item in selection]
    first = await capture_connection(
        assets,
        "connection-1",
        args.raw_directory / "connection-1.jsonl",
        args.timeout_seconds,
    )
    disconnected_at = utc_iso()
    await asyncio.sleep(0.5)
    second = await capture_connection(
        assets,
        "connection-2",
        args.raw_directory / "connection-2.jsonl",
        args.timeout_seconds,
    )

    comparisons = []
    for asset_id in assets:
        envelope = await asyncio.to_thread(fetch_book_envelope, asset_id)
        raw_path = args.raw_directory / f"rest-after-reconnect-{asset_id}.json"
        raw_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ws_book = second["books"][asset_id]
        rest_book = envelope["payload"]
        ws_top = book_top(ws_book)
        rest_top = book_top(rest_book)
        comparisons.append({
            "asset_id": asset_id,
            "websocket_hash": ws_book.get("hash"),
            "rest_hash": rest_book.get("hash"),
            "hash_match": ws_book.get("hash") == rest_book.get("hash"),
            "websocket_top": ws_top,
            "rest_top": rest_top,
            "top_match": ws_top == rest_top,
            "rest_requested_at_utc": envelope["requested_at_utc"],
            "rest_received_at_utc": envelope["received_at_utc"],
        })
    accepted = (
        all(item["full_book_count"] == len(assets) for item in (first, second))
        and second["delta_before_book_count"] == 0
        and second["recovery_seconds"] <= args.timeout_seconds
        and all(item["hash_match"] or item["top_match"] for item in comparisons)
    )
    return {
        "schema_version": "0.1.0",
        "started_at_utc": started_at,
        "websocket_url": WS_URL,
        "selection": selection,
        "acceptance_criteria": {
            "full_books_each_connection": len(assets),
            "second_connection_delta_before_book_max": 0,
            "reconnect_timeout_seconds": args.timeout_seconds,
            "rest_reconciliation": "same hash OR same executable best bid/ask per token",
        },
        "forced_disconnect_at_utc": disconnected_at,
        "connections": [
            {key: value for key, value in item.items() if key != "books"}
            for item in (first, second)
        ],
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
