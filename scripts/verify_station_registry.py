#!/usr/bin/env python3
"""Verify candidate station identities and timezones, then promote safe records."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from weather_quant.normalization.resolution_rules import validate_resolution_record
from weather_quant.normalization.station_verification import timezone_at_point


AWC_URL = "https://aviationweather.gov/api/data/stationinfo"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--station-metadata", type=Path, required=True)
    parser.add_argument("--timezone-boundaries", type=Path, required=True)
    parser.add_argument("--timezone-names", type=Path, required=True)
    parser.add_argument("--identity-review", type=Path, required=True)
    parser.add_argument("--boundary-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists() or args.evidence_output.exists():
        raise FileExistsError("verification outputs must be new immutable paths")
    candidates = [json.loads(line) for line in args.candidate.read_text(encoding="utf-8").splitlines()]
    stations = {item["icaoId"]: item for item in json.loads(args.station_metadata.read_text(encoding="utf-8"))}
    reviews = json.loads(args.identity_review.read_text(encoding="utf-8"))["records"]
    timezone_names = json.loads(args.timezone_names.read_text(encoding="utf-8"))
    with zipfile.ZipFile(args.timezone_boundaries) as archive:
        member = archive.namelist()[0]
        with archive.open(member) as source:
            timezone_features = json.load(source)["features"]

    station_hash = sha256(args.station_metadata)
    boundary_hash = sha256(args.timezone_boundaries)
    names_hash = sha256(args.timezone_names)
    output_records = []
    evidence = []
    for record in candidates:
        record["schema_version"] = "0.2.0"
        record["provenance"].update({
            "station_metadata_source_url": None,
            "station_metadata_sha256": None,
            "timezone_boundary_version": None,
            "timezone_boundary_sha256": None,
            "timezone_names_sha256": None,
            "parser_version": "0.2.0",
        })
        if record["disposition"] != "CANDIDATE_STATION_UNVERIFIED":
            validate_resolution_record(record)
            output_records.append(record)
            continue

        code = record["rule"]["station_code"]
        station = stations.get(code)
        review = reviews.get(code)
        if not station or not review:
            raise ValueError(f"missing verification input for {code}")
        boundary_timezone = timezone_at_point(float(station["lon"]), float(station["lat"]), timezone_features)
        equivalent_names = timezone_names.get(boundary_timezone, [boundary_timezone])
        timezone_match = record["rule"]["timezone"] in equivalent_names
        identity_match = review["status"] == "MATCH"
        evidence.append({
            "event_id": record["event_id"], "station_code": code,
            "rule_station_name": record["rule"]["station_name"], "official_station_name": station["site"],
            "latitude": station["lat"], "longitude": station["lon"],
            "proposed_timezone": record["rule"]["timezone"], "boundary_timezone": boundary_timezone,
            "timezone_match": timezone_match, "identity_status": review["status"], "identity_basis": review["basis"],
        })
        record["provenance"].update({
            "station_metadata_source_url": AWC_URL,
            "station_metadata_sha256": station_hash,
            "timezone_boundary_version": args.boundary_version,
            "timezone_boundary_sha256": boundary_hash,
            "timezone_names_sha256": names_hash,
        })
        if identity_match and timezone_match:
            record["disposition"] = "RECONCILED"
            record["exclusion_reasons"] = []
        else:
            record["disposition"] = "NO_TRADE_AMBIGUOUS_RULE"
            reasons = []
            if not identity_match:
                reasons.append("RULE_STATION_NAME_SOURCE_CODE_MISMATCH")
            if not timezone_match:
                reasons.append("STATION_TIMEZONE_BOUNDARY_MISMATCH")
            record["exclusion_reasons"] = reasons
        validate_resolution_record(record)
        output_records.append(record)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        for record in output_records:
            destination.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    evidence_document = {
        "schema_version": "0.1.0", "station_metadata_source_url": AWC_URL,
        "station_metadata_sha256": station_hash, "timezone_boundary_version": args.boundary_version,
        "timezone_boundary_sha256": boundary_hash, "records": evidence,
        "timezone_names_sha256": names_hash,
    }
    args.evidence_output.write_text(json.dumps(evidence_document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "record_count": len(output_records),
        "reconciled_count": sum(x["disposition"] == "RECONCILED" for x in output_records),
        "no_trade_count": sum(x["disposition"].startswith("NO_TRADE") for x in output_records),
        "timezone_match_count": sum(x["timezone_match"] for x in evidence),
        "identity_mismatch_count": sum(x["identity_status"] != "MATCH" for x in evidence),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
