#!/usr/bin/env python3
"""Run a restart-safe public WebSocket stability capture with REST anchors."""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from shakeout_polymarket_websocket import select_liquid_assets
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rest-coverage", type=Path, required=True)
    parser.add_argument("--asset-count", type=int, default=12)
    parser.add_argument("--duration-seconds", type=float, default=86400.0)
    parser.add_argument("--checkpoint-seconds", type=float, default=60.0)
    parser.add_argument("--anchor-seconds", type=float, default=300.0)
    parser.add_argument("--initial-timeout-seconds", type=float, default=15.0)
    parser.add_argument("--max-backoff-seconds", type=float, default=30.0)
    parser.add_argument("--gate-minimum-seconds", type=float, default=86400.0)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def initial_metrics() -> dict[str, Any]:
    return {
        "connection_attempt_count": 0,
        "reconnect_count": 0,
        "connection_error_count": 0,
        "connected_seconds": 0.0,
        "ready_seconds": 0.0,
        "frame_count": 0,
        "raw_bytes": 0,
        "heartbeat_sent_count": 0,
        "pong_received_count": 0,
        "full_book_event_count": 0,
        "price_change_event_count": 0,
        "applied_change_count": 0,
        "tick_change_count": 0,
        "delta_before_book_count": 0,
        "advertised_top_mismatch_count": 0,
        "max_interframe_gap_seconds": 0.0,
        "checkpoint_count": 0,
        "ready_checkpoint_count": 0,
        "missed_checkpoint_count": 0,
        "anchor_count": 0,
        "anchor_asset_count": 0,
        "anchor_match_count": 0,
        "anchor_error_count": 0,
        "errors": [],
    }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def checkpoint_payload(
    started_at: datetime,
    target_end_at: datetime,
    selection: list[dict[str, Any]],
    metrics: dict[str, Any],
    status: str,
    gate_minimum_seconds: float,
) -> dict[str, Any]:
    now = utc_now()
    elapsed = max((now - started_at).total_seconds(), 0.0)
    useful_uptime = metrics["ready_seconds"] / elapsed if elapsed else 0.0
    checkpoint_coverage = (
        metrics["ready_checkpoint_count"] / metrics["checkpoint_count"]
        if metrics["checkpoint_count"]
        else 0.0
    )
    anchor_match_rate = (
        metrics["anchor_match_count"] / metrics["anchor_asset_count"]
        if metrics["anchor_asset_count"]
        else None
    )
    return {
        "schema_version": "0.1.0",
        "status": status,
        "started_at_utc": utc_iso(started_at),
        "updated_at_utc": utc_iso(now),
        "target_end_at_utc": utc_iso(target_end_at),
        "target_duration_seconds": (target_end_at - started_at).total_seconds(),
        "elapsed_seconds": elapsed,
        "selection": selection,
        "metrics": metrics,
        "derived": {
            "useful_uptime_rate": useful_uptime,
            "ready_checkpoint_coverage": checkpoint_coverage,
            "rest_anchor_match_rate": anchor_match_rate,
        },
        "gate": {
            "minimum_elapsed_seconds": gate_minimum_seconds,
            "useful_uptime_rate_min": 0.99,
            "ready_checkpoint_coverage_min": 0.95,
            "delta_before_book_max": 0,
            "advertised_top_mismatch_max": 0,
        },
    }


async def fetch_anchor(
    assets: list[str], state: RecoveryState, run_directory: Path, anchor_index: int
) -> tuple[int, int, int]:
    anchor_directory = run_directory / "rest_anchors" / f"anchor-{anchor_index:05d}"
    anchor_directory.mkdir(parents=True)
    results = await asyncio.gather(
        *(asyncio.to_thread(fetch_book_envelope, asset_id) for asset_id in assets),
        return_exceptions=True,
    )
    compared = matched = errors = 0
    summary = []
    for asset_id, result in zip(assets, results):
        if isinstance(result, Exception):
            errors += 1
            summary.append({"asset_id": asset_id, "error": f"{type(result).__name__}: {result}"})
            continue
        atomic_json(anchor_directory / f"token-{asset_id}.json", result)
        compared += 1
        websocket_book = state.books.get(asset_id)
        hash_match = bool(
            websocket_book and websocket_book.get("hash") == result["payload"].get("hash")
        )
        top_match = bool(websocket_book and book_top(websocket_book) == book_top(result["payload"]))
        matched += hash_match or top_match
        summary.append(
            {
                "asset_id": asset_id,
                "hash_match": hash_match,
                "top_match": top_match,
                "rest_requested_at_utc": result["requested_at_utc"],
                "rest_received_at_utc": result["received_at_utc"],
            }
        )
    atomic_json(
        anchor_directory / "summary.json",
        {"observed_at_utc": utc_iso(), "records": summary},
    )
    return compared, matched, errors


def collect_finished_anchors(
    tasks: dict[int, asyncio.Task[tuple[int, int, int]]], metrics: dict[str, Any]
) -> None:
    for anchor_index, task in list(tasks.items()):
        if not task.done():
            continue
        del tasks[anchor_index]
        try:
            compared, matched, errors = task.result()
        except Exception as error:
            metrics["anchor_error_count"] += 1
            metrics["errors"].append(
                {"observed_at_utc": utc_iso(), "error": f"anchor: {type(error).__name__}: {error}"}
            )
        else:
            metrics["anchor_asset_count"] += compared
            metrics["anchor_match_count"] += matched
            metrics["anchor_error_count"] += errors


def account_checkpoint_slots(
    started_at: datetime,
    checkpoint_seconds: float,
    metrics: dict[str, Any],
    ready_now: bool,
) -> int:
    elapsed = max((utc_now() - started_at).total_seconds(), 0.0)
    expected_slots = int(elapsed // checkpoint_seconds)
    due_slots = max(expected_slots - metrics["checkpoint_count"], 0)
    if due_slots:
        metrics["checkpoint_count"] += due_slots
        metrics["missed_checkpoint_count"] += max(due_slots - 1, 0)
        metrics["ready_checkpoint_count"] += int(ready_now)
    return due_slots


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.resume:
        previous = json.loads(args.summary.read_text(encoding="utf-8"))
        started_at = parse_utc(previous["started_at_utc"])
        target_end_at = parse_utc(previous["target_end_at_utc"])
        selection = previous["selection"]
        metrics = previous["metrics"]
    else:
        if args.run_directory.exists() or args.summary.exists():
            raise FileExistsError("new stability outputs require unused paths")
        args.run_directory.mkdir(parents=True)
        started_at = utc_now()
        target_end_at = started_at + timedelta(seconds=args.duration_seconds)
        selection = select_liquid_assets(args.rest_coverage, args.asset_count)
        metrics = initial_metrics()
    for key, value in initial_metrics().items():
        metrics.setdefault(key, value)
    assets = [item["asset_id"] for item in selection]
    atomic_json(
        args.summary,
        checkpoint_payload(
            started_at,
            target_end_at,
            selection,
            metrics,
            "RUNNING",
            args.gate_minimum_seconds,
        ),
    )
    for item in selection:
        if item.get("end_at") and parse_utc(item["end_at"]) <= target_end_at:
            raise ValueError("selected market expires before the stability horizon")
    backoff = 1.0
    last_frame_at: float | None = None
    next_checkpoint = monotonic() + args.checkpoint_seconds
    next_anchor = monotonic() + args.anchor_seconds
    anchor_tasks: dict[int, asyncio.Task[tuple[int, int, int]]] = {}
    existing_connections = [
        int(path.stem.split("-")[1]) for path in args.run_directory.glob("connection-*.jsonl")
    ]
    if existing_connections:
        metrics["connection_attempt_count"] = max(
            metrics["connection_attempt_count"], max(existing_connections)
        )

    while utc_now() < target_end_at:
        metrics["connection_attempt_count"] += 1
        connection_id = metrics["connection_attempt_count"]
        state = RecoveryState(frozenset(assets))
        connected_started = monotonic()
        connected_accounted_at = connected_started
        ready_started: float | None = None
        ready_accounted_at: float | None = None
        raw_path = args.run_directory / f"connection-{connection_id:05d}.jsonl"
        sequence = 0
        try:
            with raw_path.open("x", encoding="utf-8") as raw_output:
                async with connect(WS_URL, ping_interval=None, close_timeout=5) as websocket:
                    await websocket.send(json.dumps({"assets_ids": assets, "type": "market"}))
                    backoff = 1.0
                    next_ping = monotonic() + 10.0
                    while utc_now() < target_end_at:
                        now = monotonic()
                        collect_finished_anchors(anchor_tasks, metrics)
                        if (
                            not state.ready
                            and now - connected_started >= args.initial_timeout_seconds
                        ):
                            raise TimeoutError("initial full-book coverage deadline exceeded")
                        if now >= next_ping:
                            await websocket.send("PING")
                            metrics["heartbeat_sent_count"] += 1
                            next_ping = now + 10.0
                        if now >= next_anchor:
                            if state.ready:
                                anchor_index = metrics["anchor_count"] + 1
                                anchor_tasks[anchor_index] = asyncio.create_task(
                                    fetch_anchor(
                                        assets,
                                        copy.deepcopy(state),
                                        args.run_directory,
                                        anchor_index,
                                    )
                                )
                                metrics["anchor_count"] += 1
                            next_anchor = monotonic() + args.anchor_seconds
                        if now >= next_checkpoint:
                            metrics["connected_seconds"] += now - connected_accounted_at
                            connected_accounted_at = now
                            if ready_accounted_at is not None:
                                metrics["ready_seconds"] += now - ready_accounted_at
                                ready_accounted_at = now
                            account_checkpoint_slots(
                                started_at,
                                args.checkpoint_seconds,
                                metrics,
                                state.ready,
                            )
                            atomic_json(
                                args.summary,
                                checkpoint_payload(
                                    started_at,
                                    target_end_at,
                                    selection,
                                    metrics,
                                    "RUNNING",
                                    args.gate_minimum_seconds,
                                ),
                            )
                            next_checkpoint = monotonic() + args.checkpoint_seconds
                        wake_at = min(next_ping, next_checkpoint, next_anchor)
                        wall_remaining = (target_end_at - utc_now()).total_seconds()
                        wait_seconds = min(max(wake_at - now, 0.001), max(wall_remaining, 0.001))
                        try:
                            raw = await asyncio.wait_for(websocket.recv(), timeout=wait_seconds)
                        except asyncio.TimeoutError:
                            continue
                        if not isinstance(raw, str):
                            raise TypeError("binary market frame is unsupported")
                        received = monotonic()
                        sequence += 1
                        record = raw_event_record(
                            raw, f"connection-{connection_id}", sequence, utc_iso()
                        )
                        encoded = json.dumps(record, sort_keys=True) + "\n"
                        raw_output.write(encoded)
                        raw_output.flush()
                        metrics["frame_count"] += 1
                        metrics["raw_bytes"] += len(encoded.encode("utf-8"))
                        if last_frame_at is not None:
                            metrics["max_interframe_gap_seconds"] = max(
                                metrics["max_interframe_gap_seconds"], received - last_frame_at
                            )
                        last_frame_at = received
                        before = dict(state.event_counts)
                        before_applied = state.applied_change_count
                        before_delta_without_base = state.delta_before_book_count
                        before_top_mismatch = state.advertised_top_mismatch_count
                        apply_events(state, decode_market_frame(raw))
                        metrics["pong_received_count"] += (
                            state.event_counts.get("pong", 0) - before.get("pong", 0)
                        )
                        metrics["full_book_event_count"] += (
                            state.event_counts.get("book", 0) - before.get("book", 0)
                        )
                        metrics["price_change_event_count"] += (
                            state.event_counts.get("price_change", 0)
                            - before.get("price_change", 0)
                        )
                        metrics["tick_change_count"] += (
                            state.event_counts.get("tick_size_change", 0)
                            - before.get("tick_size_change", 0)
                        )
                        metrics["applied_change_count"] += (
                            state.applied_change_count - before_applied
                        )
                        metrics["delta_before_book_count"] += (
                            state.delta_before_book_count - before_delta_without_base
                        )
                        metrics["advertised_top_mismatch_count"] += (
                            state.advertised_top_mismatch_count - before_top_mismatch
                        )
                        if state.desynchronized:
                            raise RuntimeError("advertised top mismatch desynchronized state")
                        if state.ready and ready_started is None:
                            ready_started = monotonic()
                            ready_accounted_at = ready_started
        except Exception as error:
            metrics["connection_error_count"] += 1
            metrics["errors"].append(
                {"observed_at_utc": utc_iso(), "error": f"{type(error).__name__}: {error}"}
            )
            metrics["errors"] = metrics["errors"][-100:]
        finally:
            ended = monotonic()
            metrics["connected_seconds"] += max(ended - connected_accounted_at, 0.0)
            if ready_accounted_at is not None:
                metrics["ready_seconds"] += max(ended - ready_accounted_at, 0.0)
            if utc_now() < target_end_at:
                metrics["reconnect_count"] += 1
                atomic_json(
                    args.summary,
                    checkpoint_payload(
                        started_at,
                        target_end_at,
                        selection,
                        metrics,
                        "RUNNING",
                        args.gate_minimum_seconds,
                    ),
                )
                remaining = max((target_end_at - utc_now()).total_seconds(), 0)
                await asyncio.sleep(min(backoff, remaining))
                backoff = min(backoff * 2, args.max_backoff_seconds)

    if anchor_tasks:
        await asyncio.gather(*anchor_tasks.values(), return_exceptions=True)
        collect_finished_anchors(anchor_tasks, metrics)
    account_checkpoint_slots(
        started_at,
        args.checkpoint_seconds,
        metrics,
        state.ready,
    )
    final = checkpoint_payload(
        started_at,
        target_end_at,
        selection,
        metrics,
        "COMPLETE",
        args.gate_minimum_seconds,
    )
    derived = final["derived"]
    final["accepted"] = (
        final["elapsed_seconds"] >= args.gate_minimum_seconds
        and derived["useful_uptime_rate"] >= 0.99
        and derived["ready_checkpoint_coverage"] >= 0.95
        and metrics["delta_before_book_count"] == 0
        and metrics["advertised_top_mismatch_count"] == 0
    )
    atomic_json(args.summary, final)
    return final


def main() -> int:
    args = parse_args()
    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("accepted", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
