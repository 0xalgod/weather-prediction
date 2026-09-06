#!/usr/bin/env python3
"""Normalize closed highest-temperature events into a multi-city research registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.ingestion.polymarket_markets import parse_json_array

TITLE_PATTERN = re.compile(r"^Highest temperature in (.+?) on .+\?$")


def city_from_title(title: str) -> str | None:
    match = TITLE_PATTERN.match(title.strip())
    return match.group(1) if match else None


def temperature_unit(description: str, markets: list[dict] | None = None) -> str | None:
    bucket_units = set()
    for market in markets or []:
        label = str(market.get("groupItemTitle") or "").upper()
        if "°F" in label:
            bucket_units.add("F")
        if "°C" in label:
            bucket_units.add("C")
    if len(bucket_units) == 1:
        return next(iter(bucket_units))
    if len(bucket_units) > 1:
        return None
    text = description.lower()
    fahrenheit = "degrees fahrenheit" in text or "°f" in text
    celsius = "degrees celsius" in text or "°c" in text
    if fahrenheit == celsius:
        return None
    return "F" if fahrenheit else "C"


def normalize_event(event: dict, source_checksum: str) -> tuple[dict | None, list[str]]:
    reasons = []
    event_id = str(event.get("id") or "")
    city = city_from_title(str(event.get("title") or ""))
    if not city:
        reasons.append("UNPARSEABLE_CITY_TITLE")
    target_date = str(event.get("eventDate") or "")
    target_date_source = "EVENT_DATE"
    try:
        date.fromisoformat(target_date)
    except ValueError:
        end_date = str(event.get("endDate") or "")[:10]
        try:
            date.fromisoformat(end_date)
            target_date = end_date
            target_date_source = "END_DATE_UTC_FALLBACK"
        except ValueError:
            reasons.append("MISSING_OR_INVALID_EVENT_DATE")
    source = str(event.get("resolutionSource") or "").strip()
    if not source:
        reasons.append("MISSING_RESOLUTION_SOURCE")
    markets = event.get("markets")
    unit = temperature_unit(
        str(event.get("description") or ""), markets if isinstance(markets, list) else None
    )
    if not unit:
        reasons.append("MISSING_OR_AMBIGUOUS_UNIT")
    if event.get("closed") is not True:
        reasons.append("EVENT_NOT_CLOSED")

    buckets = []
    winners = []
    if not isinstance(markets, list) or not markets:
        reasons.append("MISSING_MARKETS")
        markets = []
    for market in markets:
        market_id = str(market.get("id") or "")
        condition_id = str(market.get("conditionId") or "")
        try:
            tokens = [
                str(value)
                for value in parse_json_array(market.get("clobTokenIds"), "clobTokenIds")
            ]
            prices = [
                str(value)
                for value in parse_json_array(market.get("outcomePrices"), "outcomePrices")
            ]
        except Exception:
            tokens, prices = [], []
        identity_complete = bool(market_id and condition_id and len(tokens) == 2 and all(tokens))
        if not identity_complete:
            reasons.append("INCOMPLETE_BUCKET_IDENTITY")
        won = market.get("umaResolutionStatus") == "resolved" and prices == ["1", "0"]
        if won:
            winners.append(market_id)
        buckets.append(
            {
                "market_id": market_id,
                "condition_id": condition_id,
                "yes_token_id": tokens[0] if len(tokens) == 2 else None,
                "no_token_id": tokens[1] if len(tokens) == 2 else None,
                "label": str(market.get("groupItemTitle") or ""),
                "terminal_yes_winner": won,
            }
        )
    if len(winners) != 1:
        reasons.append("TERMINAL_WINNER_COUNT_NOT_ONE")
    reasons = sorted(set(reasons))
    if reasons:
        return None, reasons
    return {
        "event_id": event_id,
        "city": city,
        "target_date": target_date,
        "target_date_source": target_date_source,
        "end_date_utc": event.get("endDate"),
        "closed_time_utc": event.get("closedTime"),
        "resolution_source": source,
        "resolution_source_domain": urlparse(source).hostname,
        "temperature_unit": unit,
        "winner_market_id": winners[0],
        "bucket_count": len(buckets),
        "buckets": buckets,
        "source_envelope_sha256": source_checksum,
    }, []


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_run = Path(config["source_run"])
    rows = []
    exclusions = []
    event_ids = []
    for event, checksum in iter_raw_events(source_run):
        event_ids.append(str(event.get("id") or ""))
        row, reasons = normalize_event(event, checksum)
        if row:
            rows.append(row)
        else:
            exclusions.append({"event_id": str(event.get("id") or ""), "reasons": reasons})
    rows.sort(key=lambda row: (row["target_date"], row["city"], row["event_id"]))
    city_counts = Counter(row["city"] for row in rows)
    source_counts = Counter(row["resolution_source_domain"] for row in rows)
    unit_counts = Counter(row["temperature_unit"] for row in rows)
    reason_counts = Counter(reason for row in exclusions for reason in row["reasons"])
    minimum_city_events = config["gates"]["minimum_events_per_research_city"]
    research_cities = {
        city: count for city, count in sorted(city_counts.items()) if count >= minimum_city_events
    }
    duplicate_count = len(event_ids) - len(set(event_ids))
    total = len(event_ids)
    summary = {
        "source_event_count": total,
        "eligible_event_count": len(rows),
        "eligible_event_rate": len(rows) / total,
        "excluded_event_count": len(exclusions),
        "duplicate_event_count": duplicate_count,
        "eligible_city_count": len(city_counts),
        "research_city_count": len(research_cities),
        "research_event_count": sum(research_cities.values()),
        "bucket_count": sum(row["bucket_count"] for row in rows),
    }
    gates = config["gates"]
    summary["passed"] = (
        total == gates["exact_source_event_count"]
        and duplicate_count <= gates["duplicate_event_count_maximum"]
        and summary["eligible_event_rate"] >= gates["minimum_eligible_event_rate"]
        and len(city_counts) >= gates["minimum_eligible_city_count"]
        and len(research_cities) >= gates["minimum_research_city_count"]
    )
    source_files = sorted(source_run.glob("*.json"))
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "source_manifest": {
            "directory": str(source_run),
            "file_count": len(source_files),
            "canonical_file_sha256": hashlib.sha256(
                "\n".join(f"{path.name}:{sha256_path(path)}" for path in source_files).encode()
            ).hexdigest(),
        },
        "summary": summary,
        "city_counts": dict(sorted(city_counts.items())),
        "research_cities": research_cities,
        "source_domain_counts": dict(source_counts.most_common()),
        "unit_counts": dict(sorted(unit_counts.items())),
        "exclusion_reason_counts": dict(sorted(reason_counts.items())),
        "exclusions": exclusions,
        "rows": rows,
        "boundary": config["boundary"],
    }
    args.output.parent.mkdir(parents=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console = {
        key: value
        for key, value in result.items()
        if key not in {"rows", "exclusions", "city_counts"}
    }
    print(json.dumps(console, indent=2, sort_keys=True))
    if not summary["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
