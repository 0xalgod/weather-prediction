"""Read-only point-in-time Polymarket CLOB order-book snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class OrderBookError(ValueError):
    """Raised when a public book violates the snapshot contract."""


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_book_envelope(token_id: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Fetch one public book without authentication and preserve raw provenance."""

    url = "https://clob.polymarket.com/book?" + urlencode({"token_id": token_id})
    requested_at = utc_iso()
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "weather-quant-research/0.1"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS host
        raw = response.read()
        status = response.status
    received_at = utc_iso()
    payload = json.loads(raw.decode("utf-8"))
    return {
        "schema_version": "0.1.0", "source": "polymarket_clob", "endpoint": url,
        "token_id_requested": token_id, "requested_at_utc": requested_at,
        "received_at_utc": received_at, "http_status": status,
        "content_sha256": hashlib.sha256(raw).hexdigest(), "payload": payload,
    }


def fetch_tick_size_envelope(token_id: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Fetch the token's current dynamic tick size with point-in-time provenance."""

    url = f"https://clob.polymarket.com/tick-size/{token_id}"
    requested_at = utc_iso()
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "weather-quant-research/0.1"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS host
        raw = response.read()
        status = response.status
    return {
        "schema_version": "0.1.0", "source": "polymarket_clob_tick_size", "endpoint": url,
        "token_id_requested": token_id, "requested_at_utc": requested_at, "received_at_utc": utc_iso(),
        "http_status": status, "content_sha256": hashlib.sha256(raw).hexdigest(),
        "payload": json.loads(raw.decode("utf-8")),
    }


def normalize_tick_size(envelope: Mapping[str, Any]) -> Decimal:
    """Validate a public dynamic tick-size response."""

    try:
        tick = Decimal(str(envelope["payload"]["minimum_tick_size"]))
    except (KeyError, TypeError, InvalidOperation) as error:
        raise OrderBookError("invalid dynamic tick-size payload") from error
    if tick <= 0 or tick >= 1:
        raise OrderBookError("dynamic tick size outside valid bounds")
    return tick


def _levels(payload: Mapping[str, Any], side: str) -> list:
    raw_levels = payload.get(side)
    if not isinstance(raw_levels, list):
        raise OrderBookError(f"{side} must be an array")
    levels = []
    for raw in raw_levels:
        if not isinstance(raw, dict):
            raise OrderBookError(f"{side} level must be an object")
        try:
            price = Decimal(str(raw["price"]))
            size = Decimal(str(raw["size"]))
        except (KeyError, InvalidOperation) as error:
            raise OrderBookError(f"invalid {side} level") from error
        if not Decimal("0") < price < Decimal("1") or size <= 0:
            raise OrderBookError(f"{side} price/size outside valid bounds")
        levels.append({"price": str(price), "size": str(size)})
    # Normalize both sides to executable best-first ordering.
    return sorted(levels, key=lambda item: Decimal(item["price"]), reverse=side == "bids")


def normalize_book(envelope: Mapping[str, Any], expected_token_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate and summarize a raw book; never invent a missing side."""

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise OrderBookError("book payload must be an object")
    asset_id = str(payload.get("asset_id") or "")
    if not asset_id or (expected_token_id is not None and asset_id != expected_token_id):
        raise OrderBookError("book asset_id mismatch")
    bids = _levels(payload, "bids")
    asks = _levels(payload, "asks")
    best_bid = Decimal(bids[0]["price"]) if bids else None
    best_ask = Decimal(asks[0]["price"]) if asks else None
    crossed = best_bid is not None and best_ask is not None and best_bid >= best_ask
    if crossed:
        quality = "CROSSED_BOOK"
    elif not bids and not asks:
        quality = "EMPTY_BOOK"
    elif not bids or not asks:
        quality = "ONE_SIDED_BOOK"
    else:
        quality = "TWO_SIDED_BOOK"
    return {
        "market": payload.get("market"), "asset_id": asset_id,
        "exchange_timestamp_ms": int(payload["timestamp"]), "book_hash": payload.get("hash"),
        "requested_at_utc": envelope["requested_at_utc"], "received_at_utc": envelope["received_at_utc"],
        "content_sha256": envelope["content_sha256"], "bids": bids, "asks": asks,
        "best_bid": str(best_bid) if best_bid is not None else None,
        "best_ask": str(best_ask) if best_ask is not None else None,
        "spread": str(best_ask - best_bid) if best_bid is not None and best_ask is not None and not crossed else None,
        "quality": quality,
    }
