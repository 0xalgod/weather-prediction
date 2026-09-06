#!/usr/bin/env python3
"""Measure exact station-coordinate coverage for the frozen multi-city sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

from weather_quant.normalization.multicity_station_mapping import station_code_from_url


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_isd_catalog(path: Path) -> dict[str, dict]:
    """Load the deterministic latest record for each exact ICAO."""

    by_icao: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            icao = str(row.get("ICAO") or "").strip().upper()
            if len(icao) == 4:
                by_icao.setdefault(icao, []).append(row)
    return {
        icao: max(rows, key=lambda row: (row["END"], row["BEGIN"]))
        for icao, rows in by_icao.items()
    }


def isd_metadata(row: dict | None, target_date: str, maximum_staleness_days: int) -> dict | None:
    """Validate coordinate and recent-activity proxy semantics."""

    if not row:
        return None
    try:
        latitude, longitude = float(row["LAT"]), float(row["LON"])
        begin = date.fromisoformat(f"{row['BEGIN'][:4]}-{row['BEGIN'][4:6]}-{row['BEGIN'][6:]}")
        end = date.fromisoformat(f"{row['END'][:4]}-{row['END'][4:6]}-{row['END'][6:]}")
        target = date.fromisoformat(target_date)
    except (KeyError, TypeError, ValueError):
        return None
    valid = (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
        and begin <= target
        and 0 <= (target - end).days <= maximum_staleness_days
    )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "official_station_name": row["STATION NAME"],
        "catalog_begin": begin.isoformat(),
        "catalog_end": end.isoformat(),
        "catalog_end_staleness_days": (target - end).days,
        "activity_semantic": "RECENT_ACTIVITY_PROXY",
    } if valid else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    selected = json.loads(Path(config["source_selected_events"]).read_text())
    evidence_path = Path(
        config.get("station_metadata_evidence") or config["known_identity_evidence"]
    )
    evidence = json.loads(evidence_path.read_text())
    metadata = {row["station_code"]: row for row in evidence["records"]}
    isd = load_isd_catalog(Path(config["station_catalog"])) if "station_catalog" in config else None
    known_mismatches = {
        row["station_code"]
        for row in evidence["records"]
        if row["identity_status"] != "MATCH"
    }
    rows = []
    for event in selected:
        station = station_code_from_url(str(event["resolution_source"]))
        station_metadata = metadata.get(station) if station else None
        if isd is not None:
            station_metadata = isd_metadata(
                isd.get(station) if station else None,
                event["target_date"],
                550,
            )
        mismatch = station in known_mismatches
        admitted = bool(station and station_metadata and not mismatch)
        rows.append(
            {
                "event_id": event["event_id"],
                "city": event["city"],
                "target_date": event["target_date"],
                "resolution_source": event["resolution_source"],
                "station_code": station,
                "latitude": station_metadata.get("latitude") if station_metadata else None,
                "longitude": station_metadata.get("longitude") if station_metadata else None,
                "identity_status": (
                    "KNOWN_MATCH"
                    if station in metadata and station not in known_mismatches
                    else "KNOWN_MISMATCH"
                    if mismatch
                    else "NOT_MANUALLY_REVIEWED"
                ),
                "catalog_metadata": station_metadata,
                "admitted": admitted,
                "exclusion_reason": (
                    None
                    if admitted
                    else "STATION_CODE_PARSE_FAILED"
                    if not station
                    else "KNOWN_IDENTITY_MISMATCH"
                    if mismatch
                    else "MISSING_OFFICIAL_COORDINATE"
                ),
            }
        )
    event_count = len(rows)
    parsed = sum(row["station_code"] is not None for row in rows)
    mapped = [row for row in rows if row["admitted"]]
    duplicate_count = event_count - len({row["event_id"] for row in rows})
    summary = {
        "selected_event_count": event_count,
        "duplicate_event_count": duplicate_count,
        "station_code_parse_count": parsed,
        "station_code_parse_rate": parsed / event_count,
        "metadata_coordinate_count": len(mapped),
        "metadata_coordinate_rate": len(mapped) / event_count,
        "mapped_city_count": len({row["city"] for row in mapped}),
        "admitted_known_identity_mismatch_count": sum(
            row["admitted"] and row["station_code"] in known_mismatches for row in rows
        ),
    }
    thresholds = config["acceptance_thresholds"]
    checks = {
        "exact_selected_event_count": event_count == thresholds["exact_selected_event_count"],
        "maximum_duplicate_event_count": duplicate_count
        <= thresholds["maximum_duplicate_event_count"],
        "minimum_station_code_parse_rate": summary["station_code_parse_rate"]
        >= thresholds["minimum_station_code_parse_rate"],
        "minimum_metadata_coordinate_rate": summary["metadata_coordinate_rate"]
        >= thresholds["minimum_metadata_coordinate_rate"],
        "minimum_mapped_city_count": summary["mapped_city_count"]
        >= thresholds["minimum_mapped_city_count"],
        "maximum_admitted_known_identity_mismatch_count": summary[
            "admitted_known_identity_mismatch_count"
        ]
        <= thresholds["maximum_admitted_known_identity_mismatch_count"],
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "selected_events_sha256": sha256(Path(config["source_selected_events"])),
        "station_evidence_sha256": sha256(evidence_path),
        "station_catalog_sha256": (
            sha256(Path(config["station_catalog"])) if "station_catalog" in config else None
        ),
        "summary": summary,
        "checks": checks,
        "decision": "STATION_MAPPING_PASS" if all(checks.values()) else "STATION_MAPPING_FAIL",
        "rows": rows,
        "boundary": config["boundary"],
    }
    args.output.parent.mkdir(parents=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
