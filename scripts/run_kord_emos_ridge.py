#!/usr/bin/env python3
"""Train and score the preregistered nested walk-forward KORD ridge model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.score_kord_annual_baselines import gaussian_vector, integer_celsius_buckets
from weather_quant.backtest.scoring import (
    mean_metrics,
    paired_bootstrap_mean_difference,
    score_probabilities,
)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def feature_vector(row: dict) -> list[float]:
    return [
        float(row["nbm_mean_f"]),
        float(row["gefs_overlap_mean_max_f"] - row["nbm_mean_f"]),
        float(row["day_of_year_sin"]),
        float(row["day_of_year_cos"]),
        float(row["nbm_version"] == "5.0"),
        float(row["gefs_exact_partition"]),
        float(row["gefs_outside_local_seconds"] / 3600),
    ]


def fit_ridge(rows: list[dict], ridge_lambda: float) -> dict[str, np.ndarray | float]:
    x = np.asarray([feature_vector(row) for row in rows], dtype=float)
    y = np.asarray([row["daily_maximum_dry_bulb_f"] for row in rows], dtype=float)
    mean_x = x.mean(axis=0)
    scale_x = x.std(axis=0)
    scale_x[scale_x == 0] = 1.0
    standardized = (x - mean_x) / scale_x
    mean_y = float(y.mean())
    gram = standardized.T @ standardized + ridge_lambda * np.eye(x.shape[1])
    coefficients = np.linalg.solve(gram, standardized.T @ (y - mean_y))
    return {
        "mean_x": mean_x,
        "scale_x": scale_x,
        "mean_y": mean_y,
        "coefficients": coefficients,
    }


def predict(model: dict[str, np.ndarray | float], row: dict) -> float:
    values = np.asarray(feature_vector(row), dtype=float)
    standardized = (values - model["mean_x"]) / model["scale_x"]
    return float(model["mean_y"] + standardized @ model["coefficients"])


def winner_index(row: dict, minimum_c: int) -> int:
    label_c = round((row["daily_maximum_dry_bulb_f"] - 32) * 5 / 9)
    return label_c - minimum_c


def select_inner(
    train: list[dict], config: dict, buckets: list[dict]
) -> tuple[float, float, float]:
    inner_count = config["inner_selection"]["blocked_validation_events"]
    inner_train, inner_validation = train[:-inner_count], train[-inner_count:]
    minimum_c = config["outcome_bins_c"]["minimum_integer"]
    floor = config["metrics"]["probability_floor"]
    candidates = []
    for ridge_lambda in config["inner_selection"]["ridge_lambdas"]:
        model = fit_ridge(inner_train, ridge_lambda)
        means = [predict(model, row) for row in inner_validation]
        for spread_scale in config["inner_selection"]["nbm_spread_scales"]:
            losses = []
            for row, mean in zip(inner_validation, means):
                spread = max(1.0, row["nbm_standard_deviation_f"] * spread_scale)
                probability = gaussian_vector(buckets, mean, spread)[
                    winner_index(row, minimum_c)
                ]
                losses.append(-math.log(max(probability, floor)))
            candidates.append(
                (math.fsum(losses) / len(losses), ridge_lambda, spread_scale)
            )
    loss, ridge_lambda, spread_scale = min(
        candidates, key=lambda item: (item[0], item[1], abs(item[2] - 1), item[2])
    )
    return ridge_lambda, spread_scale, loss


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
    rows = sorted(
        (
            row
            for row in source["rows"]
            if row["target_date"] <= config["eligibility"]["development_end_date"]
        ),
        key=lambda row: row["target_date"],
    )
    if len(rows) != config["eligibility"]["expected_rows"]:
        raise ValueError("development row count changed")
    bins = config["outcome_bins_c"]
    buckets = integer_celsius_buckets(bins["minimum_integer"], bins["maximum_integer"])
    initial = config["outer_walk_forward"]["initial_train_events"]
    floor = config["metrics"]["probability_floor"]
    events = []
    for index in range(initial, len(rows)):
        train, target = rows[:index], rows[index]
        ridge_lambda, spread_scale, inner_loss = select_inner(train, config, buckets)
        model = fit_ridge(train, ridge_lambda)
        model_mean = predict(model, target)
        model_spread = max(1.0, target["nbm_standard_deviation_f"] * spread_scale)
        raw_spread = max(1.0, target["nbm_standard_deviation_f"])
        winning_index = winner_index(target, bins["minimum_integer"])
        events.append(
            {
                "target_date": target["target_date"],
                "train_event_count": index,
                "selected_ridge_lambda": ridge_lambda,
                "selected_spread_scale": spread_scale,
                "inner_validation_log_loss": inner_loss,
                "model_mean_f": model_mean,
                "model_spread_f": model_spread,
                "raw": score_probabilities(
                    gaussian_vector(buckets, target["nbm_mean_f"], raw_spread),
                    winning_index,
                    floor,
                ),
                "emos_ridge": score_probabilities(
                    gaussian_vector(buckets, model_mean, model_spread),
                    winning_index,
                    floor,
                ),
            }
        )
    raw_metrics = mean_metrics([row["raw"] for row in events])
    model_metrics = mean_metrics([row["emos_ridge"] for row in events])
    difference = paired_bootstrap_mean_difference(
        [row["emos_ridge"]["multiclass_log_loss"] for row in events],
        [row["raw"]["multiclass_log_loss"] for row in events],
        config["metrics"]["paired_date_bootstrap_repetitions"],
        config["metrics"]["paired_date_bootstrap_seed"],
    )
    relative = (
        raw_metrics["multiclass_log_loss"] - model_metrics["multiclass_log_loss"]
    ) / raw_metrics["multiclass_log_loss"]
    brier_difference = (
        model_metrics["multiclass_brier_score"] - raw_metrics["multiclass_brier_score"]
    )
    thresholds = config["promotion_thresholds"]
    promoted = (
        len(events) == thresholds["exact_oos_events"]
        and relative >= thresholds["relative_log_loss_improvement_minimum"]
        and brier_difference <= thresholds["brier_difference_maximum"]
        and difference["ci95_upper"] < thresholds["bootstrap_ci95_upper_below"]
    )
    selections = Counter(
        f"lambda={row['selected_ridge_lambda']},scale={row['selected_spread_scale']}"
        for row in events
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "quality": {"oos_event_count": len(events), "passed": len(events) == 178},
        "raw_oos_metrics": raw_metrics,
        "emos_ridge_oos_metrics": model_metrics,
        "relative_log_loss_improvement": relative,
        "brier_difference": brier_difference,
        "emos_minus_raw_log_loss_bootstrap": difference,
        "promotion_gate_passed": promoted,
        "decision": "FREEZE_PROSPECTIVE_CHALLENGER" if promoted else "REJECT_MODEL_V1",
        "selection_counts": dict(selections),
        "interpretation": "CONSUMED_DEVELOPMENT_EVIDENCE_NOT_INDEPENDENT_FINAL_TEST",
        "trading_authorized": False,
        "events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console = {key: value for key, value in result.items() if key not in {"events"}}
    print(json.dumps(console, indent=2))
    if not result["quality"]["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
