#!/usr/bin/env python3
"""Measure preregistered KORD NBM residual and uncertainty drift slices."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def population_std(values: list[float]) -> float:
    mean = math.fsum(values) / len(values)
    return math.sqrt(math.fsum((value - mean) ** 2 for value in values) / len(values))


def metrics(rows: list[dict], z_values: dict[str, float]) -> dict[str, float | int]:
    residuals = [row["daily_maximum_dry_bulb_f"] - row["nbm_mean_f"] for row in rows]
    standardized = [
        residual / max(row["nbm_standard_deviation_f"], 1.0)
        for residual, row in zip(residuals, rows)
    ]
    result: dict[str, float | int] = {
        "count": len(rows),
        "mean_residual_f": math.fsum(residuals) / len(rows),
        "residual_standard_deviation_f": population_std(residuals),
        "mae_f": math.fsum(abs(value) for value in residuals) / len(rows),
        "rmse_f": math.sqrt(math.fsum(value**2 for value in residuals) / len(rows)),
        "standardized_residual_mean": math.fsum(standardized) / len(rows),
        "standardized_residual_standard_deviation": population_std(standardized),
    }
    for level, z_value in z_values.items():
        result[f"central_{level}_coverage"] = sum(
            abs(value) <= z_value for value in standardized
        ) / len(standardized)
    return result


def grouped_metrics(rows: list[dict], field: str, z_values: dict[str, float]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if field == "month":
            value = date.fromisoformat(row["target_date"]).month
        else:
            value = row[field]
        groups[str(value)].append(row)
    return {key: metrics(value, z_values) for key, value in sorted(groups.items())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_path = Path(config["source"])
    if sha256_path(source_path) != config["source_file_sha256"]:
        raise ValueError("source checksum mismatch")
    source = json.loads(source_path.read_text())
    if source["rows_sha256"] != config["source_rows_sha256"]:
        raise ValueError("source rows checksum mismatch")
    rows = [
        row
        for row in source["rows"]
        if row["target_date"] <= config["eligibility"]["development_end_date"]
    ]
    if len(rows) != config["eligibility"]["expected_development_rows"]:
        raise ValueError("development row count changed")
    z_values = config["normal_interval_z"]
    slices = {field: grouped_metrics(rows, field, z_values) for field in config["groups"]}
    versions = slices["nbm_version"]
    thresholds = config["diagnostic_thresholds"]
    if any(
        row["count"] < thresholds["minimum_rows_per_version"] for row in versions.values()
    ):
        raise ValueError("insufficient rows in a version slice")
    version_rows = list(versions.values())
    bias_difference = abs(
        version_rows[0]["mean_residual_f"] - version_rows[1]["mean_residual_f"]
    )
    spreads = [row["residual_standard_deviation_f"] for row in version_rows]
    spread_ratio = max(spreads) / min(spreads)
    drift_flags = {
        "version_bias_difference": bias_difference
        >= thresholds["absolute_version_bias_difference_f"],
        "version_residual_spread_ratio": spread_ratio
        >= thresholds["version_residual_spread_ratio"],
        "any_version_central_80_miscalibration": any(
            abs(row["central_80_coverage"] - 0.8)
            > thresholds["central_80_absolute_coverage_error"]
            for row in version_rows
        ),
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "overall": metrics(rows, z_values),
        "slices": slices,
        "version_comparison": {
            "absolute_bias_difference_f": bias_difference,
            "residual_spread_ratio": spread_ratio,
        },
        "drift_flags": drift_flags,
        "shared_calibration_unsafe": any(drift_flags.values()),
        "interpretation": "CONSUMED_DEVELOPMENT_DIAGNOSTIC_NOT_NEW_OOS_EVIDENCE",
        "trading_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
