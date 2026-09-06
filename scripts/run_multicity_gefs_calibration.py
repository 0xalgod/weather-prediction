#!/usr/bin/env python3
"""Select global GEFS calibration on development and evaluate validation once."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.backtest.scoring import mean_metrics, score_probabilities
from weather_quant.market_model.vertical_slice import normal_cdf

MODELS = ("normalized_market", "raw_gefs", "calibrated_gefs", "fixed_calibrated_blend")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gaussian_vector(buckets: list[dict], mean_f: float, sd_f: float) -> list[float]:
    values = []
    for bucket in buckets:
        lower = (
            0.0
            if bucket["lower_threshold_f"] is None
            else normal_cdf(bucket["lower_threshold_f"], mean_f, sd_f)
        )
        upper = (
            1.0
            if bucket["upper_threshold_f"] is None
            else normal_cdf(bucket["upper_threshold_f"], mean_f, sd_f)
        )
        values.append(max(0.0, upper - lower))
    total = math.fsum(values)
    return [value / total for value in values]


def signed_interval_distance(mean_f: float, bucket: dict) -> float:
    lower, upper = bucket["lower_threshold_f"], bucket["upper_threshold_f"]
    if lower is not None and mean_f < lower:
        return mean_f - lower
    if upper is not None and mean_f > upper:
        return mean_f - upper
    return 0.0


def score_gefs(row: dict, bias: float, multiplier: float, floor_f: float, floor: float) -> dict:
    sd = max(row["gefs_overlap_spread_at_mean_max_f"] * multiplier, floor_f)
    probabilities = gaussian_vector(
        row["buckets"], row["gefs_overlap_mean_max_f"] + bias, sd
    )
    return {
        "probabilities": probabilities,
        "metrics": score_probabilities(probabilities, row["winner_index"], floor),
        "standard_deviation_f": sd,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_path = Path(config["source"])
    if sha256(source_path) != config["source_file_sha256"]:
        raise ValueError("source checksum mismatch")
    source = json.loads(source_path.read_text())
    if source["rows_sha256"] != config["source_rows_sha256"]:
        raise ValueError("source rows checksum mismatch")
    policy = config["data_policy"]
    development = [
        row for row in source["rows"] if row["target_date"] <= policy["development_end_date"]
    ]
    validation = [
        row
        for row in source["rows"]
        if policy["validation_start_date"] <= row["target_date"] <= policy["validation_end_date"]
    ]
    floor = config["calibration_grid"]["probability_floor"]
    candidates = []
    for bias, multiplier, floor_f in itertools.product(
        config["calibration_grid"]["bias_f"],
        config["calibration_grid"]["spread_multiplier"],
        config["calibration_grid"]["standard_deviation_floor_f"],
    ):
        losses = [
            score_gefs(row, bias, multiplier, floor_f, floor)["metrics"][
                "multiclass_log_loss"
            ]
            for row in development
        ]
        candidates.append(
            {
                "bias_f": bias,
                "spread_multiplier": multiplier,
                "standard_deviation_floor_f": floor_f,
                "development_log_loss": math.fsum(losses) / len(losses),
            }
        )
    candidates.sort(
        key=lambda row: (
            row["development_log_loss"],
            abs(row["bias_f"]),
            row["spread_multiplier"],
            row["standard_deviation_floor_f"],
        )
    )
    selected = candidates[0]
    events = []
    invalid_vectors = 0
    for row in [*development, *validation]:
        market = [bucket["market_probability_normalized"] for bucket in row["buckets"]]
        raw = score_gefs(row, 0, 1, 1, floor)
        calibrated = score_gefs(
            row,
            selected["bias_f"],
            selected["spread_multiplier"],
            selected["standard_deviation_floor_f"],
            floor,
        )
        blend = [
            0.5 * market_value + 0.5 * gefs_value
            for market_value, gefs_value in zip(market, calibrated["probabilities"])
        ]
        vectors = {
            "normalized_market": market,
            "raw_gefs": raw["probabilities"],
            "calibrated_gefs": calibrated["probabilities"],
            "fixed_calibrated_blend": blend,
        }
        invalid_vectors += sum(abs(math.fsum(vector) - 1) > 1e-9 for vector in vectors.values())
        winner_bucket = row["buckets"][row["winner_index"]]
        events.append(
            {
                "event_id": row["event_id"],
                "target_date": row["target_date"],
                "split": "development" if row in development else "validation",
                "temperature_unit": row["temperature_unit"],
                "gefs_exact_partition": row["gefs_exact_partition"],
                "raw_mean_signed_winner_interval_distance_f": signed_interval_distance(
                    row["gefs_overlap_mean_max_f"], winner_bucket
                ),
                "models": {
                    model: score_probabilities(vector, row["winner_index"], floor)
                    for model, vector in vectors.items()
                },
            }
        )
    by_split = {
        split: [event for event in events if event["split"] == split]
        for split in ("development", "validation")
    }
    metrics = {
        split: {
            model: mean_metrics([event["models"][model] for event in rows])
            for model in MODELS
        }
        for split, rows in by_split.items()
    }
    val = metrics["validation"]
    market_loss = val["normalized_market"]["multiclass_log_loss"]
    blend_loss = val["fixed_calibrated_blend"]["multiclass_log_loss"]
    relative_improvement = (market_loss - blend_loss) / market_loss
    brier_difference = (
        val["fixed_calibrated_blend"]["multiclass_brier_score"]
        - val["normalized_market"]["multiclass_brier_score"]
    )
    gate = config["decision_gate"]
    validation_clusters = len({row["target_date"] for row in validation})
    checks = {
        "exact_development_event_count": len(development) == gate["exact_development_event_count"],
        "exact_validation_event_count": len(validation) == gate["exact_validation_event_count"],
        "minimum_validation_date_cluster_count": validation_clusters
        >= gate["minimum_validation_date_cluster_count"],
        "minimum_relative_validation_log_loss_improvement_vs_market": relative_improvement
        >= gate["minimum_relative_validation_log_loss_improvement_vs_market"],
        "maximum_validation_brier_difference_vs_market": brier_difference
        <= gate["maximum_validation_brier_difference_vs_market"],
        "maximum_invalid_probability_vector_count": invalid_vectors
        <= gate["maximum_invalid_probability_vector_count"],
    }
    distances = [event["raw_mean_signed_winner_interval_distance_f"] for event in events]
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_sha256": sha256(source_path),
        "selected_calibration": selected,
        "candidate_count": len(candidates),
        "top_candidates": candidates[:10],
        "metrics": metrics,
        "validation_blend_vs_market": {
            "relative_log_loss_improvement": relative_improvement,
            "brier_difference": brier_difference,
        },
        "diagnostics": {
            "development_event_count": len(development),
            "validation_event_count": len(validation),
            "validation_date_cluster_count": validation_clusters,
            "invalid_probability_vector_count": invalid_vectors,
            "raw_mean_inside_winner_interval_rate": sum(value == 0 for value in distances)
            / len(distances),
            "raw_mean_signed_interval_distance_f": math.fsum(distances) / len(distances),
        },
        "checks": checks,
        "decision": (
            "CALIBRATED_GEFS_BLEND_RESEARCH_SIGNAL"
            if all(checks.values())
            else "CALIBRATED_GEFS_BLEND_REJECT"
        ),
        "events": events,
        "boundary": config["boundary"],
    }
    args.output.parent.mkdir(parents=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "events"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
