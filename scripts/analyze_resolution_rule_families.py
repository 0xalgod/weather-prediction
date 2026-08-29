#!/usr/bin/env python3
"""Measure station, unit and rule-template revisions across closed city families."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict

from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.normalization.manual_reconciliation import parse_resolution_rule
from weather_quant.normalization.resolution_rules import canonical_rule_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"output exists: {args.output}")
    families: Dict[str, list] = defaultdict(list)
    parse_failures = []
    for event, page_checksum in iter_raw_events(args.raw_directory):
        title = str(event.get("title") or "")
        city = title.split("Highest temperature in ", 1)[1].rsplit(" on ", 1)[0]
        markets = event.get("markets") or []
        description = str(markets[0].get("description") or event.get("description") or "") if markets else str(event.get("description") or "")
        parsed = parse_resolution_rule(description, event.get("resolutionSource"))
        template = canonical_rule_template(description) if description else ""
        record = {
            "event_id": str(event["id"]), "end_date": event.get("endDate"),
            "station_code": parsed.get("station_code"), "station_name": parsed.get("station_name"),
            "unit": parsed.get("unit"),
            "template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest() if template else None,
            "page_content_sha256": page_checksum,
        }
        families[city].append(record)
        if not parsed.get("rule_parse_complete"):
            parse_failures.append({"city": city, **record})

    city_summaries = {}
    for city, records in sorted(families.items()):
        stations = sorted({x["station_code"] for x in records if x["station_code"]})
        units = sorted({x["unit"] for x in records if x["unit"]})
        templates = sorted({x["template_sha256"] for x in records if x["template_sha256"]})
        station_transitions = []
        previous = None
        for record in sorted(records, key=lambda x: (x["end_date"] or "", x["event_id"])):
            current = record["station_code"]
            if current and previous and current != previous:
                station_transitions.append({"event_id": record["event_id"], "end_date": record["end_date"], "from": previous, "to": current})
            if current:
                previous = current
        city_summaries[city] = {
            "event_count": len(records), "station_codes": stations, "units": units,
            "rule_template_count": len(templates), "station_transitions": station_transitions,
            "missing_rule_count": sum(not x["station_code"] or not x["unit"] for x in records),
        }

    output = {
        "schema_version": "0.1.0",
        "source_raw_directory": str(args.raw_directory),
        "event_count": sum(len(x) for x in families.values()),
        "city_count": len(families),
        "rule_parse_complete_count": sum(len(x) for x in families.values()) - len(parse_failures),
        "rule_parse_failure_count": len(parse_failures),
        "cities_with_multiple_station_codes": sorted(city for city, x in city_summaries.items() if len(x["station_codes"]) > 1),
        "cities_with_multiple_units": sorted(city for city, x in city_summaries.items() if len(x["units"]) > 1),
        "cities_with_multiple_rule_templates": sorted(city for city, x in city_summaries.items() if x["rule_template_count"] > 1),
        "station_code_event_counts": dict(sorted(Counter(x["station_code"] for records in families.values() for x in records if x["station_code"]).items())),
        "city_summaries": city_summaries,
        "parse_failures": parse_failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("event_count", "city_count", "rule_parse_complete_count", "rule_parse_failure_count", "cities_with_multiple_station_codes", "cities_with_multiple_units")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
