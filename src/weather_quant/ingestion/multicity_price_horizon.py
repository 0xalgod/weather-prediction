"""Deterministic sampling and time-correct multi-horizon price coverage."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from weather_quant.ingestion.polymarket_price_history import parse_utc

JsonObject = dict[str, Any]


def stratified_two_per_city(
    rows: Sequence[Mapping[str, Any]], research_cities: set[str]
) -> list[JsonObject]:
    """Choose one lower-median event from each temporal half per city."""

    by_city: dict[str, list[JsonObject]] = defaultdict(list)
    for row in rows:
        city = str(row["city"])
        if city in research_cities:
            by_city[city].append(dict(row))
    selected: list[JsonObject] = []
    for city in sorted(research_cities):
        candidates = sorted(
            by_city[city], key=lambda row: (str(row["target_date"]), str(row["event_id"]))
        )
        if len(candidates) < 2:
            raise ValueError(f"city has fewer than two events: {city}")
        split = len(candidates) // 2
        early, late = candidates[:split], candidates[split:]
        selected.extend([early[(len(early) - 1) // 2], late[(len(late) - 1) // 2]])
    selected.sort(key=lambda row: (str(row["city"]), str(row["target_date"])))
    return selected


def latest_point_at_or_before(history: Any, cutoff_ts: int) -> tuple[int, float] | None:
    """Return the latest valid point without admitting post-cutoff observations."""

    if not isinstance(history, list):
        return None
    eligible = []
    for point in history:
        if not isinstance(point, dict) or "t" not in point or "p" not in point:
            continue
        timestamp, price = int(point["t"]), float(point["p"])
        if timestamp <= cutoff_ts and 0 <= price <= 1:
            eligible.append((timestamp, price))
    return max(eligible, key=lambda value: value[0]) if eligible else None


def event_horizon_coverage(
    event: Mapping[str, Any],
    histories: Mapping[str, Sequence[Mapping[str, Any]]],
    horizons_hours: Sequence[int],
    maximum_staleness_seconds: int,
) -> list[JsonObject]:
    """Measure full-vector availability and staleness for one event."""

    end = parse_utc(str(event["end_date_utc"]))
    buckets = list(event["buckets"])
    rows = []
    for horizon in horizons_hours:
        cutoff = end - timedelta(hours=int(horizon))
        cutoff_ts = int(cutoff.timestamp())
        points = []
        for bucket in buckets:
            token_id = str(bucket["yes_token_id"])
            selected = latest_point_at_or_before(histories.get(token_id), cutoff_ts)
            if selected:
                points.append(
                    {
                        "market_id": bucket["market_id"],
                        "yes_token_id": token_id,
                        "timestamp": selected[0],
                        "price": selected[1],
                        "staleness_seconds": cutoff_ts - selected[0],
                    }
                )
        complete = len(points) == len(buckets)
        max_staleness = max((point["staleness_seconds"] for point in points), default=None)
        usable = (
            complete
            and max_staleness is not None
            and max_staleness <= maximum_staleness_seconds
        )
        raw_sum = sum(point["price"] for point in points) if complete else None
        rows.append(
            {
                "event_id": event["event_id"],
                "city": event["city"],
                "target_date": event["target_date"],
                "horizon_hours": int(horizon),
                "cutoff_utc": datetime.fromtimestamp(cutoff_ts, tz=cutoff.tzinfo).isoformat(),
                "bucket_count": len(buckets),
                "available_bucket_count": len(points),
                "complete_vector": complete,
                "usable_full_vector": usable,
                "maximum_staleness_seconds": max_staleness,
                "raw_probability_sum": raw_sum,
                "points": points,
            }
        )
    return rows


def summarize_horizons(rows: Sequence[Mapping[str, Any]]) -> JsonObject:
    """Aggregate coverage by horizon and across cities."""

    event_count = len({str(row["event_id"]) for row in rows})
    cities_with_any = {
        str(row["city"]) for row in rows if row.get("usable_full_vector") is True
    }
    by_horizon: JsonObject = {}
    for horizon in sorted({int(row["horizon_hours"]) for row in rows}):
        subset = [row for row in rows if int(row["horizon_hours"]) == horizon]
        usable = [row for row in subset if row.get("usable_full_vector") is True]
        complete = [row for row in subset if row.get("complete_vector") is True]
        by_horizon[str(horizon)] = {
            "event_count": len(subset),
            "complete_vector_event_count": len(complete),
            "complete_vector_event_rate": len(complete) / len(subset) if subset else 0.0,
            "usable_full_vector_event_count": len(usable),
            "usable_full_vector_event_rate": len(usable) / len(subset) if subset else 0.0,
            "city_count_with_usable_vector": len({str(row["city"]) for row in usable}),
        }
    return {
        "event_count": event_count,
        "cities_with_usable_vector_at_any_horizon_count": len(cities_with_any),
        "by_horizon": by_horizon,
    }
