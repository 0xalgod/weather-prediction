"""Leakage-aware helpers for the locked Chicago historical join."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from weather_quant.ingestion.polymarket_markets import (
    DiscoveryError,
    parse_json_array,
)
from weather_quant.normalization.resolution_rules import (
    build_bucket_records,
    validate_bucket_partition,
)

_TITLE_DATE = re.compile(r"\bon (?P<month>[A-Z][a-z]+) (?P<day>\d{1,2})\?")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_date_from_event(event: Mapping[str, Any]) -> date:
    """Cross-check title month/day against the UTC end-date calendar date."""

    end_date = datetime.fromisoformat(str(event["endDate"]).replace("Z", "+00:00")).date()
    match = _TITLE_DATE.search(str(event.get("title") or ""))
    if match is None:
        raise DiscoveryError(f"event {event.get('id')} title date is unparseable")
    title_date = datetime.strptime(
        f"{end_date.year} {match.group('month')} {match.group('day')}", "%Y %B %d"
    ).date()
    if title_date != end_date:
        raise DiscoveryError(f"event {event.get('id')} title/end date mismatch")
    return title_date


def event_join_identity(event: Mapping[str, Any]) -> dict[str, Any]:
    """Create the outcome/bucket side of one joined historical record."""

    target_date = target_date_from_event(event)
    buckets = build_bucket_records(event["markets"], "F")
    validate_bucket_partition(buckets, 1.0)
    winners: list[str] = []
    for market in event["markets"]:
        outcomes = parse_json_array(market.get("outcomes"), "outcomes")
        prices = parse_json_array(market.get("outcomePrices"), "outcomePrices")
        if outcomes != ["Yes", "No"] or len(prices) != 2:
            raise DiscoveryError(f"event {event['id']} outcome order is invalid")
        normalized_prices = [float(value) for value in prices]
        if normalized_prices == [1.0, 0.0]:
            winners.append(str(market["id"]))
        elif normalized_prices != [0.0, 1.0]:
            raise DiscoveryError(f"event {event['id']} has non-terminal outcome prices")
    if len(winners) != 1:
        raise DiscoveryError(f"event {event['id']} has {len(winners)} winning buckets")
    winning_market_id = winners[0]
    winning_bucket = next(bucket for bucket in buckets if bucket["market_id"] == winning_market_id)
    decision_time = datetime.combine(target_date - timedelta(days=1), time(11), tzinfo=timezone.utc)
    target_valid_time = datetime.combine(
        target_date + timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    return {
        "event_id": str(event["id"]),
        "event_title": event["title"],
        "target_local_date": target_date.isoformat(),
        "decision_time_utc": decision_time.isoformat().replace("+00:00", "Z"),
        "forecast_run_date": (target_date - timedelta(days=1)).strftime("%Y%m%d"),
        "target_valid_time_utc": target_valid_time.isoformat().replace("+00:00", "Z"),
        "winning_market_id": winning_market_id,
        "winning_bucket_label": winning_bucket["label"],
        "buckets": buckets,
    }


def exact_target_record(
    records: Sequence[Mapping[str, Any]], target_valid_time_utc: str
) -> dict[str, Any]:
    """Require one complete probabilistic MaxT record at the locked valid time."""

    matches = [
        dict(record) for record in records if record["valid_time_utc"] == target_valid_time_utc
    ]
    if len(matches) != 1:
        raise DiscoveryError(f"expected one target forecast record, found {len(matches)}")
    record = matches[0]
    required = (
        "mean_f",
        "standard_deviation_f",
        "p10_f",
        "p25_f",
        "p50_f",
        "p75_f",
        "p90_f",
    )
    if any(record.get(field) is None for field in required):
        raise DiscoveryError("target forecast has missing distribution values")
    return record


def index_events(
    events: Iterable[Mapping[str, Any]], expected_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Return exact events in locked file order and reject missing/duplicate identities."""

    wanted = set(expected_ids)
    found: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for event in events:
        event_id = str(event.get("id") or "")
        if event_id not in wanted:
            continue
        if event_id in found:
            duplicates.add(event_id)
        found[event_id] = dict(event)
    if duplicates or set(found) != wanted:
        raise DiscoveryError(
            f"identity mismatch missing={sorted(wanted - set(found))} "
            f"duplicates={sorted(duplicates)}"
        )
    return [found[event_id] for event_id in expected_ids]


def select_chicago_date_range(
    events: Iterable[Mapping[str, Any]], start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Select exact closed/resolved Chicago events in an inclusive date range."""

    selected = []
    seen_dates: set[date] = set()
    for event in events:
        title = str(event.get("title") or "")
        if "chicago" not in title.lower() or event.get("closed") is not True:
            continue
        target_date = target_date_from_event(event)
        if not start_date <= target_date <= end_date:
            continue
        identity = event_join_identity(event)
        if target_date in seen_dates:
            raise DiscoveryError(f"duplicate Chicago target date: {target_date}")
        seen_dates.add(target_date)
        selected.append({**dict(event), "_join_identity": identity})
    selected.sort(key=lambda event: event["_join_identity"]["target_local_date"])
    return selected


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
