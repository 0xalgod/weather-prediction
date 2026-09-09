#!/usr/bin/env python3
"""Download NOAA LCDv2 and build a frozen two-year KORD hourly panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path
from weather_quant.ingestion.noaa_lcdv2 import parse_lcdv2_hourly, parse_lcdv2_sod


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--raw-output", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.raw_output.exists() or a.output.exists():
        raise FileExistsError("immutable output exists")
    c = json.loads(a.config.read_text())
    station = c["station"]
    a.raw_output.mkdir(parents=True)
    objects = []
    hourly = []
    sod = []
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for year in c["source"]["years"]:
        filename = f"LCD_{station['ghcn_id']}_{year}.csv"
        url = f"{c['source']['base_url']}/{year}/{filename}"
        req = urllib.request.Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
        with urllib.request.urlopen(req, timeout=120) as response:
            content = response.read()
            headers = {
                "etag": response.headers.get("ETag", "").strip(),
                "last_modified": response.headers.get("Last-Modified", ""),
            }
        path = a.raw_output / filename
        path.write_bytes(content)
        hourly.extend(parse_lcdv2_hourly(content))
        sod.extend(parse_lcdv2_sod(content))
        objects.append(
            {
                "url": url,
                "filename": filename,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "headers": headers,
                "retrieved_at_utc": retrieved,
            }
        )
    start = date.fromisoformat(c["window"]["start_date"])
    end = date.fromisoformat(c["window"]["end_date"])
    targets = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    target_set = {x.isoformat() for x in targets}
    input_set = {(x - timedelta(days=1)).isoformat() for x in targets}
    hourly = [r for r in hourly if r["date_local_standard"] in input_set]
    labels = [r for r in sod if r["date"] in target_set]
    label_counts = Counter(r["date"] for r in labels)
    temp_hours = defaultdict(set)
    for r in hourly:
        if r["dry_bulb_c"] is not None:
            temp_hours[r["date_local_standard"]].add(r["hour_local_standard"])
    identity_errors = sum(
        r["station"] != station["ghcn_id"] or r["name"] != station["name"] for r in hourly + labels
    )
    duplicate_sod = sum(n > 1 for n in label_counts.values())
    out_of_range = sum(
        r["dry_bulb_c"] is not None and not -60 <= r["dry_bulb_c"] <= 60 for r in hourly
    )
    labeled = {r["date"] for r in labels if r["daily_maximum_dry_bulb_c"] is not None}
    days18 = sum(len(temp_hours[d]) >= 18 for d in input_set)
    summary = {
        "target_day_count": len(targets),
        "hourly_row_count": len(hourly),
        "label_row_count": len(labels),
        "non_null_label_count": len(labeled),
        "label_coverage": len(labeled) / len(targets),
        "days_with_18_temperature_hours": days18,
        "days_with_18_temperature_hours_rate": days18 / len(targets),
        "identity_error_count": identity_errors,
        "duplicate_sod_date_count": duplicate_sod,
        "out_of_range_temperature_count": out_of_range,
        "first_hourly_timestamp": min(r["timestamp_local_standard"] for r in hourly),
        "last_hourly_timestamp": max(r["timestamp_local_standard"] for r in hourly),
    }
    g = c["acceptance_thresholds"]
    checks = {
        "exact_target_day_count": summary["target_day_count"] == g["exact_target_day_count"],
        "minimum_label_coverage": summary["label_coverage"] >= g["minimum_label_coverage"],
        "minimum_days_with_18_temperature_hours_rate": summary[
            "days_with_18_temperature_hours_rate"
        ]
        >= g["minimum_days_with_18_temperature_hours_rate"],
        "maximum_identity_error_count": identity_errors <= g["maximum_identity_error_count"],
        "maximum_duplicate_sod_date_count": duplicate_sod <= g["maximum_duplicate_sod_date_count"],
        "maximum_out_of_range_temperature_count": out_of_range
        <= g["maximum_out_of_range_temperature_count"],
    }
    a.output.mkdir(parents=True)
    hp = a.output / "hourly.jsonl"
    lp = a.output / "labels.jsonl"
    hp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in hourly))
    lp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in labels))
    result = {
        "experiment_id": c["experiment_id"],
        "generated_at_utc": retrieved,
        "config_sha256": sha256_path(a.config),
        "objects": objects,
        "artifacts": {"hourly_sha256": sha256_path(hp), "labels_sha256": sha256_path(lp)},
        "summary": summary,
        "checks": checks,
        "decision": "KORD_HOURLY_DATASET_PASS"
        if all(checks.values())
        else "KORD_HOURLY_DATASET_FAIL",
        "boundary": c["boundary"],
    }
    (a.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "objects"}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
