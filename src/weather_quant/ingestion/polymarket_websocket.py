"""Public Polymarket market-WebSocket parsing and recovery state."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
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
    applied_change_count: int = 0
    advertised_top_mismatch_count: int = 0
    desynchronized: bool = False

    @staticmethod
    def _decimal(value: Any, field_name: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError) as error:
            raise WebSocketContractError(f"invalid {field_name}") from error

    def _apply_price_change(self, change: Mapping[str, Any]) -> None:
        asset_id = str(change.get("asset_id") or "")
        if asset_id not in self.expected_assets:
            return
        if asset_id not in self.books:
            self.delta_before_book_count += 1
            return
        side = str(change.get("side") or "").upper()
        side_name = {"BUY": "bids", "SELL": "asks"}.get(side)
        if side_name is None:
            raise WebSocketContractError("price_change side must be BUY or SELL")
        price = self._decimal(change.get("price"), "price_change price")
        size = self._decimal(change.get("size"), "price_change size")
        if not Decimal("0") < price < Decimal("1") or size < 0:
            raise WebSocketContractError("price_change price/size outside valid bounds")
        book = self.books[asset_id]
        levels = book.get(side_name)
        if not isinstance(levels, list):
            raise WebSocketContractError(f"book {side_name} must be an array")
        retained = [level for level in levels if Decimal(str(level["price"])) != price]
        if size > 0:
            retained.append({"price": str(price), "size": str(size)})
        retained.sort(
            key=lambda level: Decimal(str(level["price"])),
            reverse=side_name == "bids",
        )
        book[side_name] = retained
        if change.get("hash") is not None:
            book["hash"] = change["hash"]
        self.applied_change_count += 1

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
            advertised_by_asset = {}
            for change in changes:
                if not isinstance(change, dict):
                    raise WebSocketContractError("price_change item must be an object")
                self._apply_price_change(change)
                asset_id = str(change.get("asset_id") or "")
                if change.get("best_bid") is not None and change.get("best_ask") is not None:
                    advertised_by_asset[asset_id] = {
                        "best_bid": format(Decimal(str(change["best_bid"])), "f"),
                        "best_ask": format(Decimal(str(change["best_ask"])), "f"),
                    }
            for asset_id, advertised in advertised_by_asset.items():
                if asset_id in self.books and advertised != book_top(self.books[asset_id]):
                    self.advertised_top_mismatch_count += 1
                    self.desynchronized = True
            return
        if event_type == "tick_size_change":
            asset_id = str(event.get("asset_id") or "")
            new_tick = event.get("new_tick_size")
            if asset_id in self.expected_assets and new_tick is not None:
                self.ticks[asset_id] = str(new_tick)

    @property
    def ready(self) -> bool:
        return not self.desynchronized and self.expected_assets.issubset(self.books)


def apply_events(state: RecoveryState, events: Iterable[Mapping[str, Any]]) -> None:
    for event in events:
        state.apply(event)


def book_top(payload: Mapping[str, Any]) -> dict[str, str | None]:
    """Return executable top-of-book from a WebSocket or REST full book."""

    def prices(side: str) -> list[Decimal]:
        levels = payload.get(side, [])
        if not isinstance(levels, list):
            raise WebSocketContractError(f"{side} must be an array")
        try:
            return [Decimal(str(level["price"])) for level in levels]
        except (InvalidOperation, KeyError, TypeError) as error:
            raise WebSocketContractError(f"invalid {side} price") from error

    bids = prices("bids")
    asks = prices("asks")
    return {
        "best_bid": format(max(bids), "f") if bids else None,
        "best_ask": format(min(asks), "f") if asks else None,
    }
