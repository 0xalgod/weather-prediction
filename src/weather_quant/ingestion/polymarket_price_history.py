"""Deterministic selection and validation for Polymarket CLOB price history."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from weather_quant.ingestion.polymarket_markets import DiscoveryError, parse_json_array

JsonObject = dict[str, Any]


def parse_utc(value: str) -> datetime:
    """Parse an ISO timestamp and require timezone awareness."""

    normalized = value.replace("Z", "+00:00")
    fractional = re.search(r"\.(\d+)(?=[+-]\d\d:\d\d$)", normalized)
    if fractional and len(fractional.group(1)) < 6:
        normalized = normalized.replace(
            f".{fractional.group(1)}", f".{fractional.group(1).ljust(6, '0')}", 1
        )
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise DiscoveryError(f"timestamp lacks timezone: {value}")
    return parsed.astimezone(timezone.utc)


def eligible_chicago_event(event: Mapping[str, Any], cutoff: datetime) -> tuple[bool, list[str]]:
    """Apply the pre-registered event and market identity rules."""

    reasons: list[str] = []
    if "chicago" not in str(event.get("title") or "").lower():
        reasons.append("CITY_MISMATCH")
    if event.get("closed") is not True:
        reasons.append("EVENT_NOT_CLOSED")
    if not event.get("creationDate"):
        reasons.append("MISSING_CREATION_TIME")
    if not event.get("closedTime"):
        reasons.append("MISSING_CLOSED_TIME")
    if not event.get("endDate"):
        reasons.append("MISSING_END_TIME")
    elif parse_utc(str(event["endDate"])) > cutoff:
        reasons.append("AFTER_CUTOFF")
    markets = event.get("markets")
    if not isinstance(markets, list) or not markets:
        reasons.append("NO_MARKETS")
        return False, sorted(set(reasons))
    for market in markets:
        if not isinstance(market, dict):
            reasons.append("INVALID_MARKET")
            continue
        if market.get("umaResolutionStatus") != "resolved":
            reasons.append("MARKET_NOT_UMA_RESOLVED")
        try:
            outcomes = parse_json_array(market.get("outcomes"), "outcomes")
            tokens = parse_json_array(market.get("clobTokenIds"), "clobTokenIds")
        except DiscoveryError:
            reasons.append("MARKET_IDENTIFIER_INCOMPLETE")
            continue
        if len(outcomes) != 2 or len(tokens) != 2 or "Yes" not in outcomes:
            reasons.append("MARKET_IDENTIFIER_INCOMPLETE")
    return not reasons, sorted(set(reasons))


def select_events(
    events: Iterable[Mapping[str, Any]], cutoff: datetime, limit: int
) -> list[JsonObject]:
    """Select latest eligible Chicago events using the locked stable order."""

    eligible = [dict(event) for event in events if eligible_chicago_event(event, cutoff)[0]]
    eligible.sort(
        key=lambda event: (parse_utc(str(event["endDate"])), int(str(event["id"]))),
        reverse=True,
    )
    return eligible[:limit]


def yes_token_rows(events: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    """Expand every selected bucket to its YES asset and integer request window."""

    rows: list[JsonObject] = []
    for event in events:
        start_ts = math.ceil(parse_utc(str(event["creationDate"])).timestamp())
        end_ts = math.floor(parse_utc(str(event["closedTime"])).timestamp())
        if start_ts > end_ts:
            raise DiscoveryError(f"event {event['id']} has an invalid request window")
        for market in event["markets"]:
            outcomes = parse_json_array(market.get("outcomes"), "outcomes")
            tokens = parse_json_array(market.get("clobTokenIds"), "clobTokenIds")
            yes_index = outcomes.index("Yes")
            rows.append(
                {
                    "event_id": str(event["id"]),
                    "event_title": event.get("title"),
                    "event_end_date": event.get("endDate"),
                    "market_id": str(market["id"]),
                    "bucket_label": market.get("groupItemTitle"),
                    "yes_token_id": str(tokens[yes_index]),
                    "request_start_ts": start_ts,
                    "request_end_ts": end_ts,
                }
            )
    return rows


def validate_history(history: Any, start_ts: int, end_ts: int) -> JsonObject:
    """Validate one documented history array and expose coverage diagnostics."""

    if not isinstance(history, list):
        raise DiscoveryError("history must be an array")
    parsed: list[tuple[int, float]] = []
    for point in history:
        if not isinstance(point, dict) or "t" not in point or "p" not in point:
            raise DiscoveryError("history point must contain t and p")
        timestamp = int(point["t"])
        price = float(point["p"])
        if not 0 <= price <= 1:
            raise DiscoveryError(f"price outside [0, 1]: {price}")
        parsed.append((timestamp, price))
    by_timestamp: dict[int, set[float]] = {}
    for timestamp, price in parsed:
        by_timestamp.setdefault(timestamp, set()).add(price)
    return {
        "point_count": len(parsed),
        "unique_timestamp_count": len(by_timestamp),
        "duplicate_point_count": len(parsed) - len(by_timestamp),
        "conflicting_timestamp_count": sum(len(prices) > 1 for prices in by_timestamp.values()),
        "out_of_window_point_count": sum(
            not start_ts <= timestamp <= end_ts for timestamp, _ in parsed
        ),
        "response_strictly_increasing": all(
            parsed[index][0] < parsed[index + 1][0] for index in range(len(parsed) - 1)
        ),
        "first_timestamp": min(by_timestamp) if by_timestamp else None,
        "last_timestamp": max(by_timestamp) if by_timestamp else None,
    }


def summarize_coverage(rows: Sequence[Mapping[str, Any]], minimum_points: int = 2) -> JsonObject:
    """Aggregate token diagnostics without dropping errors or empty histories."""

    token_count = len(rows)
    event_ids = sorted({str(row["event_id"]) for row in rows})
    covered = [row for row in rows if row.get("request_ok") and int(row.get("point_count", 0)) > 0]
    sufficiently_covered = [row for row in covered if int(row["point_count"]) >= minimum_points]
    covered_events = {str(row["event_id"]) for row in covered}
    errors = [row for row in rows if not row.get("request_ok")]
    total_points = sum(int(row.get("point_count", 0)) for row in rows)
    out_of_window = sum(int(row.get("out_of_window_point_count", 0)) for row in rows)
    return {
        "selected_event_count": len(event_ids),
        "token_count": token_count,
        "events_with_any_history_count": len(covered_events),
        "events_with_any_history_rate": len(covered_events) / len(event_ids) if event_ids else 0.0,
        "tokens_with_any_history_count": len(covered),
        "tokens_with_any_history_rate": len(covered) / token_count if token_count else 0.0,
        "tokens_with_minimum_points_count": len(sufficiently_covered),
        "covered_tokens_meeting_minimum_rate": (
            len(sufficiently_covered) / len(covered) if covered else 0.0
        ),
        "request_error_count": len(errors),
        "request_error_rate": len(errors) / token_count if token_count else 0.0,
        "total_point_count": total_points,
        "out_of_window_point_count": out_of_window,
        "out_of_window_point_rate": out_of_window / total_points if total_points else 0.0,
        "duplicate_point_count": sum(int(row.get("duplicate_point_count", 0)) for row in rows),
        "conflicting_timestamp_count": sum(
            int(row.get("conflicting_timestamp_count", 0)) for row in rows
        ),
        "non_strict_response_count": sum(
            row.get("request_ok") is True
            and int(row.get("point_count", 0)) > 1
            and row.get("response_strictly_increasing") is not True
            for row in rows
        ),
    }
