"""Public Polymarket market-WebSocket parsing and recovery state."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


class WebSocketContractError(ValueError):
    """Raised when a market-channel message violates the local contract."""


def decode_market_frame(raw: str) -> list[dict[str, Any]]:
    """Decode one frame, preserving heartbeats and expanding event arrays."""

    if raw == "PONG":
        return [{"event_type": "pong"}]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise WebSocketContractError("market frame is neither PONG nor JSON") from error
    events = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(event, dict) for event in events):
        raise WebSocketContractError("market frame events must be objects")
    return events


def raw_event_record(
    raw: str, connection_id: str, sequence: int, received_at_utc: str
) -> dict[str, Any]:
    """Create an immutable provenance record for an exact WebSocket frame."""

    return {
        "schema_version": "0.1.0",
        "source": "polymarket_clob_market_websocket",
        "connection_id": connection_id,
        "sequence": sequence,
        "received_at_utc": received_at_utc,
        "content_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "raw": raw,
    }


@dataclass
class RecoveryState:
    """Fail-closed state: deltas are usable only after a full book per asset."""

    expected_assets: frozenset
    books: dict[str, dict[str, Any]] = field(default_factory=dict)
    ticks: dict[str, str] = field(default_factory=dict)
    event_counts: dict[str, int] = field(default_factory=dict)
    delta_before_book_count: int = 0

    def apply(self, event: Mapping[str, Any]) -> None:
        event_type = str(event.get("event_type") or "unknown")
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        if event_type == "book":
            asset_id = str(event.get("asset_id") or "")
            if asset_id in self.expected_assets:
                self.books[asset_id] = dict(event)
            return
        if event_type == "price_change":
            changes = event.get("price_changes")
            if not isinstance(changes, list):
                raise WebSocketContractError("price_change.price_changes must be an array")
            for change in changes:
                asset_id = str(change.get("asset_id") or "") if isinstance(change, dict) else ""
                if asset_id in self.expected_assets and asset_id not in self.books:
                    self.delta_before_book_count += 1
            return
        if event_type == "tick_size_change":
            asset_id = str(event.get("asset_id") or "")
            new_tick = event.get("new_tick_size")
            if asset_id in self.expected_assets and new_tick is not None:
                self.ticks[asset_id] = str(new_tick)

    @property
    def ready(self) -> bool:
        return self.expected_assets.issubset(self.books)


def apply_events(state: RecoveryState, events: Iterable[Mapping[str, Any]]) -> None:
    for event in events:
        state.apply(event)


def book_top(payload: Mapping[str, Any]) -> dict[str, str | None]:
    """Return executable top-of-book from a WebSocket or REST full book."""

    def prices(side: str) -> list[float]:
        levels = payload.get(side, [])
        if not isinstance(levels, list):
            raise WebSocketContractError(f"{side} must be an array")
        try:
            return [float(level["price"]) for level in levels]
        except (KeyError, TypeError, ValueError) as error:
            raise WebSocketContractError(f"invalid {side} price") from error

    bids = prices("bids")
    asks = prices("asks")
    return {
        "best_bid": format(max(bids), "g") if bids else None,
        "best_ask": format(min(asks), "g") if asks else None,
    }
