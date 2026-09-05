"""Strict classification for prospective Chicago/KORD capture cohorts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone
from typing import Any

from weather_quant.ingestion.polymarket_markets import (
    DiscoveryError,
    isoformat_utc,
    parse_json_array,
    parse_source_timestamp,
)


def audit_upcoming_kord_candidate(event: Mapping[str, Any], as_of: datetime) -> dict[str, Any]:
    """Classify one raw Gamma event against the preregistered live KORD gate."""
    title = str(event.get("title") or "")
    description = str(event.get("description") or "")
    resolution_source = str(event.get("resolutionSource") or "")
    end_at = parse_source_timestamp(event.get("endDate"))
    event_date_text = str(event.get("eventDate") or "")
    try:
        event_date = datetime.fromisoformat(event_date_text).date()
        decision_at = datetime.combine(
            event_date - timedelta(days=1), time(11), timezone.utc
        )
    except ValueError:
        event_date = None
        decision_at = None
    markets = event.get("markets")
    identity_failures = []
    token_identities = []
    if not isinstance(markets, list) or not markets:
        identity_failures.append("MISSING_MARKETS")
        markets = []
    for market in markets:
        if not isinstance(market, dict):
            identity_failures.append("INVALID_MARKET")
            continue
        market_id = str(market.get("id") or "")
        condition_id = str(market.get("conditionId") or "")
        try:
            tokens = parse_json_array(market.get("clobTokenIds"), "clobTokenIds")
        except DiscoveryError:
            tokens = []
        complete = (
            bool(market_id)
            and bool(condition_id)
            and len(tokens) == 2
            and all(str(item) for item in tokens)
        )
        if not complete:
            identity_failures.append(f"INCOMPLETE_MARKET_IDENTITY:{market_id or 'UNKNOWN'}")
        else:
            token_identities.append(
                {
                    "market_id": market_id,
                    "condition_id": condition_id,
                    "token_ids": [str(item) for item in tokens],
                }
            )

    source_lower = resolution_source.lower()
    description_lower = description.lower()
    supported_primary = (
        "wunderground.com" in source_lower and "/kord" in source_lower
    ) or (
        "weather.gov/wrh/timeseries" in source_lower
        and ("site=kord" in source_lower or "site=KORD" in resolution_source)
    )
    checks = {
        "chicago_title_family": title.startswith("Highest temperature in Chicago on ")
        and title.endswith("?"),
        "active": event.get("active") is True,
        "not_closed": event.get("closed") is False,
        "end_at_present": end_at is not None,
        "observed_future": end_at is not None and end_at >= as_of.astimezone(timezone.utc),
        "decision_time_future": decision_at is not None
        and decision_at >= as_of.astimezone(timezone.utc),
        "primary_resolution_source_supported_kord": supported_primary,
        "rule_names_kord": "kord" in description_lower
        or "chicago o'hare intl airport station" in description_lower,
        "rule_has_following_date_trigger": "first data point for the following date"
        in description_lower
        or "first datapoint for the following date" in description_lower,
        "nested_market_identities_complete": not identity_failures,
    }
    return {
        "event_id": str(event.get("id") or ""),
        "title": title,
        "end_at": isoformat_utc(end_at) if end_at else None,
        "target_local_date": event_date.isoformat() if event_date else None,
        "decision_at": isoformat_utc(decision_at) if decision_at else None,
        "resolution_source": resolution_source or None,
        "rule_text_sha256": hashlib.sha256(description.encode("utf-8")).hexdigest(),
        "checks": checks,
        "qualified": all(checks.values()),
        "identity_failures": identity_failures,
        "token_identities": token_identities,
    }
