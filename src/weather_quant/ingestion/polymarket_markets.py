"""Read-only Polymarket Gamma discovery and strict market normalization.

The client preserves source bytes inside a checksummed envelope before any
normalization. It never signs requests and contains no order-placement code.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen


JsonObject = Dict[str, Any]
ByteRequester = Callable[[str, Mapping[str, str], float], bytes]

_TITLE_PATTERN = re.compile(r"^Highest temperature in (?P<city>.+) on (?P<date_label>.+)\?$")


class DiscoveryError(RuntimeError):
    """Raised when public discovery data violates a required contract."""


@dataclass(frozen=True)
class NormalizedEvent:
    """Normalized event, market, outcome and exclusion records."""

    event: JsonObject
    markets: Tuple[JsonObject, ...]
    outcomes: Tuple[JsonObject, ...]
    exclusions: Tuple[JsonObject, ...]


def utc_now() -> datetime:
    """Return an aware UTC timestamp; isolated for deterministic tests."""

    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    """Serialize an aware timestamp in canonical UTC form."""

    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_source_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 source timestamp without discarding timezone data."""

    if value is None:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise DiscoveryError("source timestamp is missing timezone information")
    return parsed.astimezone(timezone.utc)


def parse_json_array(value: Any, field_name: str) -> List[Any]:
    """Parse Gamma fields that may be JSON strings or native arrays."""

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise DiscoveryError(f"{field_name} is not valid JSON") from error
    else:
        parsed = value
    if not isinstance(parsed, list):
        raise DiscoveryError(f"{field_name} must be a JSON array")
    return parsed


def _default_requester(url: str, headers: Mapping[str, str], timeout: float) -> bytes:
    request = Request(url, headers=dict(headers), method="GET")
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS base URL
        return response.read()


class GammaDiscoveryClient:
    """Public, read-only Gamma client with keyset pagination."""

    def __init__(
        self,
        base_url: str = "https://gamma-api.polymarket.com",
        user_agent: str = "weather-quant-research/0.1",
        timeout_seconds: float = 30.0,
        requester: Optional[ByteRequester] = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("Gamma base URL must use HTTPS")
        self.base_url = base_url.rstrip("/")
        self.headers = {"Accept": "application/json", "User-Agent": user_agent}
        self.timeout_seconds = timeout_seconds
        self.requester = requester or _default_requester
        self.clock = clock

    def build_url(self, path: str, parameters: Mapping[str, Any]) -> str:
        """Build a deterministic Gamma URL from an endpoint and parameters."""

        if not path.startswith("/"):
            raise ValueError("path must begin with a slash")
        encoded = urlencode(sorted(parameters.items()), doseq=True)
        return f"{self.base_url}{path}?{encoded}" if encoded else f"{self.base_url}{path}"

    def get_envelope(self, path: str, parameters: Mapping[str, Any]) -> JsonObject:
        """Fetch public JSON and return a point-in-time raw envelope."""

        requested_at = self.clock()
        url = self.build_url(path, parameters)
        raw = self.requester(url, self.headers, self.timeout_seconds)
        received_at = self.clock()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DiscoveryError(f"invalid JSON response from {path}") from error

        return {
            "schema_version": "0.1.0",
            "source": "polymarket_gamma",
            "endpoint": f"{self.base_url}{path}",
            "request_parameters": dict(parameters),
            "source_timestamp": None,
            "requested_at_utc": isoformat_utc(requested_at),
            "received_at_utc": isoformat_utc(received_at),
            "http_status": 200,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "payload": payload,
        }

    def iter_event_envelopes(
        self,
        tag_slug: str = "highest-temperature",
        closed: bool = False,
        page_size: int = 500,
        max_pages: int = 1000,
    ) -> Iterator[JsonObject]:
        """Yield every keyset page and reject cursor loops or malformed pages."""

        if page_size < 1:
            raise ValueError("page_size must be positive")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")

        cursor: Optional[str] = None
        seen_cursors = set()
        for _ in range(max_pages):
            parameters: Dict[str, Any] = {
                "ascending": "true",
                "closed": str(closed).lower(),
                "limit": page_size,
                "order": "endDate",
                "tag_slug": tag_slug,
            }
            if cursor is not None:
                parameters["after_cursor"] = cursor

            envelope = self.get_envelope("/events/keyset", parameters)
            payload = envelope["payload"]
            if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
                raise DiscoveryError("keyset response must contain an events array")
            yield envelope

            next_cursor = payload.get("next_cursor")
            if next_cursor in (None, ""):
                return
            if not isinstance(next_cursor, str):
                raise DiscoveryError("next_cursor must be a string or null")
            if next_cursor in seen_cursors:
                raise DiscoveryError("keyset cursor loop detected")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        raise DiscoveryError("keyset pagination exceeded max_pages safety limit")


def write_raw_envelope(envelope: Mapping[str, Any], destination: Path) -> Path:
    """Atomically persist a raw envelope without overwriting existing evidence."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"raw envelope already exists: {destination}")
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    serialized = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with temporary.open("x", encoding="utf-8") as output:
        output.write(serialized)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(destination)
    return destination


def normalize_highest_temperature_event(event: Mapping[str, Any], as_of: datetime) -> NormalizedEvent:
    """Normalize one MaxT event and classify unusable nested markets explicitly."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    event_id = str(event.get("id") or "")
    title = str(event.get("title") or "")
    match = _TITLE_PATTERN.match(title)
    if not event_id:
        raise DiscoveryError("event id is required")
    if match is None:
        raise DiscoveryError("event title does not match the highest-temperature contract family")

    end_at = parse_source_timestamp(event.get("endDate"))
    if end_at is None:
        raise DiscoveryError("event endDate is required")
    temporally_relevant = end_at >= as_of.astimezone(timezone.utc)
    normalized_event: JsonObject = {
        "event_id": event_id,
        "title": title,
        "slug": event.get("slug"),
        "city_label": match.group("city"),
        "date_label": match.group("date_label"),
        "end_at": isoformat_utc(end_at),
        "active": bool(event.get("active")),
        "closed": bool(event.get("closed")),
        "archived": bool(event.get("archived")),
        "temporally_relevant": temporally_relevant,
        "resolution_source": event.get("resolutionSource"),
        "negative_risk": bool(event.get("negRisk") or event.get("enableNegRisk")),
    }

    normalized_markets: List[JsonObject] = []
    normalized_outcomes: List[JsonObject] = []
    exclusions: List[JsonObject] = []
    raw_markets = event.get("markets")
    if not isinstance(raw_markets, list):
        raise DiscoveryError("event markets must be an array")

    for market in raw_markets:
        if not isinstance(market, dict):
            raise DiscoveryError("nested market must be an object")
        market_id = str(market.get("id") or "")
        reason_codes: List[str] = []
        condition_id = str(market.get("conditionId") or "")
        try:
            outcome_labels = parse_json_array(market.get("outcomes"), "outcomes")
            token_ids = parse_json_array(market.get("clobTokenIds"), "clobTokenIds")
        except DiscoveryError as error:
            reason_codes.append("INVALID_OUTCOME_TOKEN_JSON")
            outcome_labels = []
            token_ids = []
            parse_error = str(error)
        else:
            parse_error = None

        if not market_id:
            reason_codes.append("MISSING_MARKET_ID")
        if not condition_id:
            reason_codes.append("MISSING_CONDITION_ID")
        if not token_ids:
            reason_codes.append("MISSING_CLOB_TOKEN_IDS")
        if len(outcome_labels) != len(token_ids):
            reason_codes.append("OUTCOME_TOKEN_LENGTH_MISMATCH")
        if len(outcome_labels) != 2:
            reason_codes.append("NON_BINARY_BUCKET_MARKET")
        if market.get("enableOrderBook") is not True:
            reason_codes.append("ORDER_BOOK_DISABLED")
        if not temporally_relevant:
            reason_codes.append("EVENT_END_DATE_PASSED")

        eligible = not reason_codes
        market_record: JsonObject = {
            "event_id": event_id,
            "market_id": market_id or None,
            "condition_id": condition_id or None,
            "question": market.get("question"),
            "slug": market.get("slug"),
            "bucket_label": market.get("groupItemTitle"),
            "order_book_enabled": market.get("enableOrderBook") is True,
            "negative_risk": bool(market.get("negRisk")),
            "minimum_tick_size": market.get("orderPriceMinTickSize"),
            "minimum_order_size": market.get("orderMinSize"),
            "fees_enabled": bool(market.get("feesEnabled")),
            "fee_schedule": market.get("feeSchedule"),
            "eligible_for_book_collection": eligible,
        }
        normalized_markets.append(market_record)

        if eligible:
            for outcome_index, (label, token_id) in enumerate(zip(outcome_labels, token_ids)):
                normalized_outcomes.append(
                    {
                        "event_id": event_id,
                        "market_id": market_id,
                        "condition_id": condition_id,
                        "outcome_index": outcome_index,
                        "outcome_label": str(label),
                        "token_id": str(token_id),
                    }
                )
        else:
            exclusions.append(
                {
                    "event_id": event_id,
                    "market_id": market_id or None,
                    "reason_codes": sorted(set(reason_codes)),
                    "parse_error": parse_error,
                }
            )

    return NormalizedEvent(
        event=normalized_event,
        markets=tuple(normalized_markets),
        outcomes=tuple(normalized_outcomes),
        exclusions=tuple(exclusions),
    )


def summarize_discovery(events: Sequence[NormalizedEvent]) -> JsonObject:
    """Return event-clustered coverage metrics without inflating token counts."""

    return {
        "event_count": len(events),
        "unique_city_count": len({item.event["city_label"] for item in events}),
        "market_count": sum(len(item.markets) for item in events),
        "eligible_market_count": sum(
            1 for item in events for market in item.markets if market["eligible_for_book_collection"]
        ),
        "outcome_count": sum(len(item.outcomes) for item in events),
        "excluded_market_count": sum(len(item.exclusions) for item in events),
        "temporally_relevant_event_count": sum(
            1 for item in events if item.event["temporally_relevant"]
        ),
    }
