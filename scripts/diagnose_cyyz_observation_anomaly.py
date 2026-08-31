#!/usr/bin/env python3
"""Diagnose the CYYZ 2026-03-08 Wunderground observation anomaly."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.ingestion.eccc import (
    fetch_geojson,
    hourly_query_url,
    round_half_up,
    station_local_rows,
)
from weather_quant.ingestion.wunderground import parse_daily_page

LOCAL_DATE = "2026-03-08"
CLIMATE_IDENTIFIER = "6158731"
EXPECTED_STATION_NAME = "TORONTO INTL A"
EXPECTED_LATITUDE = 43.679
EXPECTED_LONGITUDE = -79.629
WU_EXPECTED_HIGH = 9
ECCC_DATASET_URL = (
    "https://open.canada.ca/data/en/dataset/"
    "df2e6e1a-6057-4c4d-a509-94aa57705a8c"
)
ECCC_TECHNICAL_DOCUMENTATION_URL = (
    "https://www.canada.ca/en/environment-climate-change/services/"
    "climate-change/canadian-centre-climate-services/display-download/"
    "technical-documentation-hourly-data.html"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wunderground-page", type=Path, required=True)
    parser.add_argument("--gamma-raw-dir", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    value = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def scan_polymarket(directory: Path) -> dict:
    total = 0
    matches = []
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        events = document.get("payload", {}).get("events", [])
        total += len(events)
        for event in events:
            title = str(event.get("title") or "")
            slug = str(event.get("slug") or "")
            description = str(event.get("description") or "")
            exact = (
                "toronto" in title.lower()
                and (
                    "march-8-2026" in slug.lower()
                    or "on 8 Mar '26." in description
                )
            )
            if exact:
                matches.append(
                    {
                        "event_id": str(event.get("id")),
                        "title": title,
                        "slug": slug,
                        "markets": len(event.get("markets", [])),
                    }
                )
    return {"scanned_event_count": total, "exact_match_count": len(matches), "matches": matches}


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.raw_output.exists():
        raise FileExistsError("outputs must be new immutable paths")
    url = hourly_query_url(
        "-79.8,43.6,-79.5,43.8",
        "2026-03-08T00:00:00Z",
        "2026-03-09T23:59:59Z",
    )
    retrieval = fetch_geojson(url)
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_bytes(retrieval.pop("raw"))
    document = retrieval.pop("document")
    rows = station_local_rows(document, CLIMATE_IDENTIFIER, LOCAL_DATE)
    temperatures = [row["TEMP"] for row in rows if row.get("TEMP") is not None]
    station_names = sorted({row["STATION_NAME"] for row in rows})
    coordinates = sorted(
        {(row["LATITUDE_DECIMAL_DEGREES"], row["LONGITUDE_DECIMAL_DEGREES"]) for row in rows}
    )
    distance_km = haversine_km(
        EXPECTED_LATITUDE,
        EXPECTED_LONGITUDE,
        coordinates[0][0],
        coordinates[0][1],
    ) if len(coordinates) == 1 else None
    wu = parse_daily_page(args.wunderground_page.read_text(encoding="utf-8", errors="replace"))
    market = scan_polymarket(args.gamma_raw_dir)
    max_temperature = max(temperatures) if temperatures else None
    rounded_max = round_half_up(max_temperature) if max_temperature is not None else None
    local_hours = [row["LOCAL_HOUR"] for row in rows]
    checks = {
        "http_200": retrieval["http_status"] == 200,
        "exact_23_rows": len(rows) == 23,
        "unique_23_local_hours": len(set(local_hours)) == 23,
        "dst_missing_hour_02": 2 not in local_hours,
        "all_temperatures_present": len(temperatures) == 23,
        "station_name_match": station_names == [EXPECTED_STATION_NAME],
        "single_coordinate": len(coordinates) == 1,
        "coordinate_within_one_km": distance_km is not None and distance_km <= 1.0,
        "wunderground_identity": wu["station_code"] == "CYYZ" and wu["page_date"] == "2026-3-8",
        "wunderground_two_rows": wu["observation_count"] == 2,
        "rounded_max_matches_wunderground": rounded_max == wu["daily_high"] == WU_EXPECTED_HIGH,
    }
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "diagnostic": "cyyz-2026-03-08-observation-anomaly",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "official_sources": {
            "hourly_dataset": ECCC_DATASET_URL,
            "technical_documentation": ECCC_TECHNICAL_DOCUMENTATION_URL,
        },
        "eccc_retrieval": retrieval,
        "eccc": {
            "climate_identifier": CLIMATE_IDENTIFIER,
            "station_names": station_names,
            "coordinates": coordinates,
            "distance_from_verified_cyyz_km": distance_km,
            "local_date": LOCAL_DATE,
            "row_count": len(rows),
            "local_hours": local_hours,
            "temperature_count": len(temperatures),
            "temperature_max_c": max_temperature,
            "temperature_max_half_up_c": rounded_max,
            "rows": rows,
        },
        "wunderground": {
            key: value for key, value in wu.items() if key != "observations"
        },
        "polymarket": {
            **market,
            "settlement_status": (
                "NOT_APPLICABLE" if market["exact_match_count"] == 0 else "AVAILABLE"
            ),
        },
        "checks": checks,
        "diagnostic_passed": all(checks.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "diagnostic_passed": artifact["diagnostic_passed"],
                "checks": checks,
                "eccc_max_c": max_temperature,
                "polymarket": artifact["polymarket"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
