#!/usr/bin/env python3
"""Probe actual ECMWF Open Data inventory, subsets, and rolling retention."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from weather_quant.ingestion.ecmwf_open_data import (
    fetch_index,
    index_url,
    inventory_index,
    retrieve_subset,
)


def head_status(url: str, timeout: float = 30.0) -> dict[str, object]:
    observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    request = Request(url, method="HEAD", headers={"User-Agent": "weather-quant-research/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return {
                "url": url,
                "observed_at_utc": observed,
                "http_status": response.status,
                "content_length": response.headers.get("Content-Length"),
                "last_modified": response.headers.get("Last-Modified"),
                "classification": "AVAILABLE" if response.status == 200 else "UNEXPECTED_STATUS",
            }
    except HTTPError as error:
        return {
            "url": url,
            "observed_at_utc": observed,
            "http_status": error.code,
            "classification": "NOT_FOUND" if error.code == 404 else "HTTP_ERROR",
        }
    except URLError as error:
        return {
            "url": url,
            "observed_at_utc": observed,
            "http_status": None,
            "classification": "TRANSIENT_ERROR",
            "error": str(error.reason),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", required=True, help="YYYYMMDD")
    parser.add_argument("--cycle", type=int, default=0)
    parser.add_argument("--step", type=int, default=24)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def existing_file(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "local_path": str(path),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "reused_from_interrupted_probe": True,
        "grib_message_count": raw.count(b"GRIB"),
        "starts_with_grib": raw.startswith(b"GRIB"),
        "ends_with_7777": raw.endswith(b"7777"),
    }


def main() -> None:
    args = parse_args()
    run_day = date.fromisoformat(
        f"{args.run_date[:4]}-{args.run_date[4:6]}-{args.run_date[6:]}"
    )
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    indexes: dict[str, object] = {}
    for stream in ("oper", "enfo"):
        url = index_url(args.run_date, args.cycle, stream, args.step)
        target = args.raw_dir / f"{stream}-step{args.step}.index"
        retrieval = existing_file(target) if target.exists() else fetch_index(url, target)
        indexes[stream] = {"retrieval": retrieval, "inventory": inventory_index(target)}

    oper_target = args.raw_dir / f"oper-fc-step{args.step}.grib2"
    pf_target = args.raw_dir / f"enfo-pf-step{args.step}.grib2"
    subsets: dict[str, object] = {
        "deterministic": existing_file(oper_target)
        if oper_target.exists()
        else retrieve_subset(
            args.run_date,
            args.cycle,
            "oper",
            "fc",
            args.step,
            oper_target,
        ),
        "perturbed": existing_file(pf_target)
        if pf_target.exists()
        else retrieve_subset(
            args.run_date,
            args.cycle,
            "enfo",
            "pf",
            args.step,
            pf_target,
            list(range(1, 51)),
        ),
    }
    try:
        subsets["control"] = retrieve_subset(
            args.run_date,
            args.cycle,
            "enfo",
            "cf",
            args.step,
            args.raw_dir / f"enfo-cf-step{args.step}.grib2",
        )
    except ValueError as error:
        subsets["control"] = {
            "status": "NOT_PRESENT_IN_INDEX",
            "error": str(error),
        }

    retention = []
    for offset in (0, 1, 2, 3, 4, 7, 30, 365):
        candidate = (run_day - timedelta(days=offset)).strftime("%Y%m%d")
        evidence = head_status(index_url(candidate, args.cycle, "oper", args.step))
        evidence["days_before_run_date"] = offset
        retention.append(evidence)

    oper_counts = indexes["oper"]["inventory"]["type_parameter_counts"]
    enfo_inventory = indexes["enfo"]["inventory"]
    enfo_counts = enfo_inventory["type_parameter_counts"]
    fields = ("2t", "mx2t3", "mn2t3")
    checks = {
        "oper_three_fields_once": all(
            oper_counts.get(f"fc:{field}") == 1 for field in fields
        ),
        "pf_three_fields_50_times": all(
            enfo_counts.get(f"pf:{field}") == 50 for field in fields
        ),
        "pf_members_exactly_1_to_50": enfo_inventory["perturbed_members"] == list(range(1, 51)),
        "retrieved_message_counts": {
            name: result.get("grib_message_count") for name, result in subsets.items()
        },
        "retrieved_grib_integrity": all(
            result.get("starts_with_grib", False) and result.get("ends_with_7777", False)
            for name, result in subsets.items()
            if name != "control"
        ),
        "control_present": subsets["control"].get("grib_message_count") == 3,
        "retention_at_least_365_days": any(
            item["days_before_run_date"] >= 365 and item["http_status"] == 200
            for item in retention
        ),
    }
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "ecmwf-open-data",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run": {"date": args.run_date, "cycle": args.cycle, "step": args.step},
        "pre_registered_acceptance": {
            "oper_counts": {"2t": 1, "mx2t3": 1, "mn2t3": 1},
            "pf_counts": {"2t": 50, "mx2t3": 50, "mn2t3": 50},
            "pf_members": "exact integers 1..50",
            "grib_messages": {"deterministic": 3, "perturbed": 150, "control": 3},
            "historical_backtest_retention_days": 365,
        },
        "indexes": indexes,
        "subsets": subsets,
        "retention": retention,
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
