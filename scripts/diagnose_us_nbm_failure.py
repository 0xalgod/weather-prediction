#!/usr/bin/env python3
"""Diagnose the rejected US NBM blend without scoring untouched test dates."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.run_us_nbm_quantile_calibration import score_rows
from weather_quant.normalization.resolution_rules import parse_bucket_bounds


def signed_interval_distance(value: float, lower: float | None, upper: float | None) -> float:
    if lower is not None and value < lower:
        return value - lower
    if upper is not None and value > upper:
        return value - upper
    return 0.0


def mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def enriched_scores(rows: list[dict], shift: float, scale: float, floor: float) -> list[dict]:
    scored = {row["event_id"]: row for row in score_rows(rows, shift, scale, floor)}
    output = []
    for row in rows:
        bucket = row["buckets"][row["winner_bucket_index"]]
        bounds = parse_bucket_bounds(bucket["label"], row["temperature_unit"])
        calibrated_median = float(row["nbm_feature"]["p50_f"]) + shift
        distance = signed_interval_distance(
            calibrated_median, bounds["lower_bound"], bounds["upper_bound"]
        )
        score = scored[row["event_id"]]
        output.append(
            {
                **score,
                "calibrated_median_f": calibrated_median,
                "winner_interval": bounds,
                "signed_median_distance_f": distance,
                "winner_interval_contained": distance == 0,
                "calibrated_spread_f": float(row["nbm_feature"]["standard_deviation_f"])
                * scale,
                "proxy_overlap_hours": row["proxy_window"]["overlap_hours"],
                "challenger_minus_market_log_loss": score["models"]["challenger"][
                    "metrics"
                ]["multiclass_log_loss"]
                - score["models"]["market"]["metrics"]["multiclass_log_loss"],
            }
        )
    return output


def group_diagnostics(rows: list[dict], key: str) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    output = {}
    for value, subset in sorted(grouped.items()):
        output[value] = {
            "event_count": len(subset),
            "mean_signed_median_distance_f": mean(
                [row["signed_median_distance_f"] for row in subset]
            ),
            "winner_interval_containment_rate": mean(
                [float(row["winner_interval_contained"]) for row in subset]
            ),
            "mean_calibrated_spread_f": mean(
                [row["calibrated_spread_f"] for row in subset]
            ),
            "mean_challenger_minus_market_log_loss": mean(
                [row["challenger_minus_market_log_loss"] for row in subset]
            ),
            "total_positive_challenger_excess_log_loss": math.fsum(
                max(0.0, row["challenger_minus_market_log_loss"]) for row in subset
            ),
            "mean_raw_nbm_log_loss": mean(
                [
                    row["models"]["raw_nbm_quantile"]["metrics"]["multiclass_log_loss"]
                    for row in subset
                ]
            ),
            "mean_calibrated_nbm_log_loss": mean(
                [
                    row["models"]["calibrated_nbm_quantile"]["metrics"][
                        "multiclass_log_loss"
                    ]
                    for row in subset
                ]
            ),
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_path = Path(config["source_dataset"])
    model_path = Path(config["source_model_result"])
    if sha256_path(source_path) != config["source_dataset_sha256"]:
        raise ValueError("source dataset checksum mismatch")
    if sha256_path(model_path) != config["source_model_result_sha256"]:
        raise ValueError("source model result checksum mismatch")
    source_rows = [json.loads(line) for line in source_path.read_text().splitlines()]
    eligible = [row for row in source_rows if row["price_eligibility"] == "PRICE_ELIGIBLE"]
    policy = config["data_policy"]
    development = [row for row in eligible if row["target_date"] in policy["development_dates"]]
    validation = [row for row in eligible if row["target_date"] in policy["validation_dates"]]
    locked = policy["locked_calibration"]
    floor = 0.000001
    dev_scores = enriched_scores(development, locked["shift_f"], locked["spread_scale"], floor)
    val_scores = enriched_scores(validation, locked["shift_f"], locked["spread_scale"], floor)
    dev_city = group_diagnostics(dev_scores, "city")
    val_city = group_diagnostics(val_scores, "city")

    material = config["diagnostics"]["material_city_bias_threshold_f"]
    stable_cities = []
    for city in sorted(dev_city):
        dev_mean = dev_city[city]["mean_signed_median_distance_f"]
        val_mean = val_city[city]["mean_signed_median_distance_f"]
        if abs(dev_mean) >= material and dev_mean * val_mean > 0:
            stable_cities.append(city)
    positive_totals = sorted(
        (
            (city, metrics["total_positive_challenger_excess_log_loss"])
            for city, metrics in val_city.items()
        ),
        key=lambda item: (-item[1], item[0]),
    )
    total_positive = math.fsum(value for _, value in positive_totals)
    top3_concentration = (
        math.fsum(value for _, value in positive_totals[:3]) / total_positive
        if total_positive > 0
        else 0.0
    )
    minimum_dev = min(row["event_count"] for row in dev_city.values())
    minimum_val = min(row["event_count"] for row in val_city.values())
    thresholds = config["go_no_go"]
    checks = {
        "minimum_stable_material_bias_city_count": len(stable_cities)
        >= thresholds["minimum_stable_material_bias_city_count"],
        "minimum_top3_positive_excess_loss_concentration": top3_concentration
        >= thresholds["minimum_top3_positive_excess_loss_concentration"],
        "minimum_development_events_per_city": minimum_dev
        >= thresholds["minimum_development_events_per_city"],
        "minimum_validation_events_per_city": minimum_val
        >= thresholds["minimum_validation_events_per_city"],
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "source_dataset_sha256": sha256_path(source_path),
        "source_model_result_sha256": sha256_path(model_path),
        "summary": {
            "development_event_count": len(development),
            "validation_event_count": len(validation),
            "test_event_count_scored": 0,
            "stable_material_bias_city_count": len(stable_cities),
            "stable_material_bias_cities": stable_cities,
            "top3_positive_excess_loss_concentration": top3_concentration,
            "top3_positive_excess_loss_cities": [city for city, _ in positive_totals[:3]],
            "minimum_development_events_per_city": minimum_dev,
            "minimum_validation_events_per_city": minimum_val,
        },
        "checks": checks,
        "decision": "CITY_OFFSET_MODEL_GO" if all(checks.values()) else "NBM_BRANCH_NO_GO",
        "development_by_city": dev_city,
        "validation_by_city": val_city,
        "development_by_overlap": group_diagnostics(dev_scores, "proxy_overlap_hours"),
        "validation_by_overlap": group_diagnostics(val_scores, "proxy_overlap_hours"),
        "boundary": config["boundary"],
    }
    args.output.mkdir(parents=True)
    (args.output / "diagnostic-events.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in dev_scores + val_scores)
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
