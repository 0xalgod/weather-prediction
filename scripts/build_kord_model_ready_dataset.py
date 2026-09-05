#!/usr/bin/env python3
"""Join checksum-identified KORD NBM, GEFS and LCDv2 data without imputation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from weather_quant.ingestion.noaa_lcdv2 import celsius_to_fahrenheit, parse_lcdv2_sod

STATION_CODE = "KORD"
STATION_ID = "USW00094846"
TIMEZONE = ZoneInfo("America/Chicago")
NBM_FIELDS = ("mean_f", "standard_deviation_f", "p10_f", "p25_f", "p50_f", "p75_f", "p90_f")
GEFS_FIELDS = (
    "gefs_overlap_mean_max_f",
    "gefs_overlap_spread_at_mean_max_f",
    "gefs_interior_mean_max_f",
    "gefs_interior_spread_at_mean_max_f",
    "gefs_max_block_spread_f",
)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def calendar_features(target: date) -> dict[str, float | int]:
    angle = 2 * math.pi * (target.timetuple().tm_yday - 1) / 365.2425
    local_noon = datetime.combine(target, time(12), TIMEZONE)
    return {
        "day_of_year_sin": math.sin(angle),
        "day_of_year_cos": math.cos(angle),
        "month": target.month,
        "dst_offset_hours": local_noon.utcoffset().total_seconds() / 3600,
    }


def decision_time(target: date) -> datetime:
    return datetime.combine(target - timedelta(days=1), time(11), timezone.utc)


def parse_http_time(value: str) -> datetime:
    from email.utils import parsedate_to_datetime

    return parsedate_to_datetime(value).astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--nbm", type=Path, required=True)
    parser.add_argument("--gefs", type=Path, required=True)
    parser.add_argument("--lcd-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("processed output directory must be immutable")

    config = json.loads(args.config.read_text())
    nbm = json.loads(args.nbm.read_text())
    gefs = json.loads(args.gefs.read_text())
    lcd_result = json.loads(args.lcd_result.read_text())
    lcd_rows = []
    for obj in lcd_result["objects"]:
        source = args.lcd_result.parent / obj["filename"]
        if sha256_path(source) != obj["sha256"]:
            raise ValueError(f"LCD checksum mismatch: {source}")
        lcd_rows.extend(parse_lcdv2_sod(source.read_bytes()))

    nbm_by_date = {row["target_date"]: row for row in nbm["rows"] if row["status"] == "ADMITTED"}
    gefs_by_date = {row["target_date"]: row for row in gefs["daily_features"] if row["complete"]}
    label_by_date = {
        row["date"]: row for row in lcd_rows
        if row["station"] == STATION_ID and row["daily_maximum_dry_bulb_c"] is not None
    }
    start = date.fromisoformat(config["scope"]["target_start_date"])
    end = date.fromisoformat(config["scope"]["target_end_date"])
    all_dates = [date.fromordinal(day) for day in range(start.toordinal(), end.toordinal() + 1)]
    rows = []
    exclusions = []
    leakage_count = 0
    for target in all_dates:
        key = target.isoformat()
        sources = (("NBM", nbm_by_date), ("GEFS", gefs_by_date), ("LABEL", label_by_date))
        missing = [name for name, values in sources if key not in values]
        if missing:
            exclusions.append({"target_date": key, "missing_sources": missing})
            continue
        nrow, grow, lrow = nbm_by_date[key], gefs_by_date[key], label_by_date[key]
        cutoff = decision_time(target)
        nbm_late = parse_http_time(nrow["source_last_modified"]) > cutoff
        gefs_messages = [r for r in gefs["rows"] if r["target_date"] == key]
        gefs_late = any(parse_http_time(r["object_last_modified"]) > cutoff for r in gefs_messages)
        leakage_count += int(nbm_late or gefs_late)
        row = {
            "station_code": STATION_CODE,
            "station_id": STATION_ID,
            "target_date": key,
            "decision_time_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "nbm_model_run_time_utc": nrow["feature"]["model_run_time_utc"],
            "nbm_valid_time_utc": nrow["feature"]["valid_time_utc"],
            "nbm_version": nrow["nbm_version"],
            **{f"nbm_{field}": nrow["feature"][field] for field in NBM_FIELDS},
            **{field: grow["features"][field] for field in GEFS_FIELDS},
            "gefs_exact_partition": grow["exact_partition"],
            "gefs_outside_local_seconds": grow["outside_local_seconds"],
            **calendar_features(target),
            "daily_maximum_dry_bulb_f": celsius_to_fahrenheit(lrow["daily_maximum_dry_bulb_c"]),
        }
        rows.append(row)

    numeric_values = [v for row in rows for v in row.values() if isinstance(v, float)]
    duplicate_count = len(rows) - len({(row["station_id"], row["target_date"]) for row in rows})
    nonfinite_count = sum(not math.isfinite(value) for value in numeric_values)
    gates = config["quality_gates"]
    expected = config["final_join"]["expected_joined_row_count"]
    summary = {
        "target_date_count": len(all_dates),
        "joined_row_count": len(rows),
        "joined_eligible_rate": len(rows) / len(all_dates),
        "excluded_row_count": len(exclusions),
        "duplicate_station_date_count": duplicate_count,
        "nonfinite_feature_or_label_count": nonfinite_count,
        "temporal_leakage_count": leakage_count,
    }
    summary["passed"] = (
        len(rows) == expected
        and summary["joined_eligible_rate"] >= gates["joined_eligible_rate_minimum"]
        and duplicate_count <= gates["duplicate_station_date_count_maximum"]
        and nonfinite_count <= gates["nonfinite_feature_or_label_count_maximum"]
        and leakage_count <= gates["temporal_leakage_count_maximum"]
    )
    artifact = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "provenance": {
            "config": {"path": str(args.config), "sha256": sha256_path(args.config)},
            "nbm": {"path": str(args.nbm), "sha256": sha256_path(args.nbm)},
            "gefs": {"path": str(args.gefs), "sha256": sha256_path(args.gefs)},
            "lcd_result": {"path": str(args.lcd_result), "sha256": sha256_path(args.lcd_result)},
        },
        "summary": summary,
        "exclusions": exclusions,
        "rows_sha256": canonical_sha256(rows),
        "rows": rows,
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "result.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({**summary, "rows_sha256": artifact["rows_sha256"]}, indent=2, sort_keys=True))
    if not summary["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
