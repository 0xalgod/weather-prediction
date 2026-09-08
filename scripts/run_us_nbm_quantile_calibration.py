#!/usr/bin/env python3
"""Fit and evaluate the preregistered US NBM quantile calibration benchmark."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from weather_quant.backtest.scoring import (
    mean_metrics,
    paired_cluster_bootstrap_mean_difference,
    score_probabilities,
)
from weather_quant.forecasting.calibration import quantile_probabilities, select_parameters
from weather_quant.normalization.resolution_rules import parse_bucket_bounds


def model_event(row: dict) -> dict:
    if row["temperature_unit"] != "F":
        raise ValueError("US pilot benchmark requires Fahrenheit buckets")
    buckets = [
        {**bucket, **parse_bucket_bounds(bucket["label"], row["temperature_unit"])}
        for bucket in row["buckets"]
    ]
    winner = row["buckets"][row["winner_bucket_index"]]["market_id"]
    return {"buckets": buckets, "forecast": row["nbm_feature"], "winning_market_id": winner}


def score_vector(probabilities: list[float], winner_index: int, floor: float) -> dict:
    return score_probabilities(probabilities, winner_index, floor)


def score_rows(rows: list[dict], shift: float, scale: float, floor: float) -> list[dict]:
    output = []
    for row in rows:
        prepared = model_event(row)
        buckets = prepared["buckets"]
        winner_index = row["winner_bucket_index"]
        market = row["market_probabilities"]
        raw_nbm = quantile_probabilities(buckets, row["nbm_feature"], 0.0, 1.0)
        calibrated = quantile_probabilities(buckets, row["nbm_feature"], shift, scale)
        challenger = [(left + right) / 2 for left, right in zip(market, calibrated)]
        uniform = [1 / len(buckets)] * len(buckets)
        vectors = {
            "uniform": uniform,
            "market": market,
            "raw_nbm_quantile": raw_nbm,
            "calibrated_nbm_quantile": calibrated,
            "challenger": challenger,
        }
        output.append(
            {
                "event_id": row["event_id"],
                "city": row["city"],
                "target_date": row["target_date"],
                "winner_bucket_index": winner_index,
                "models": {
                    name: {
                        "probabilities": vector,
                        "metrics": score_vector(vector, winner_index, floor),
                    }
                    for name, vector in vectors.items()
                },
            }
        )
    return output


def aggregate(scores: list[dict]) -> dict:
    names = scores[0]["models"]
    return {
        name: mean_metrics([row["models"][name]["metrics"] for row in scores])
        for name in names
    }


def gate(scores: list[dict], config: dict) -> tuple[dict, dict]:
    metrics = aggregate(scores)
    market_loss = metrics["market"]["multiclass_log_loss"]
    challenger_loss = metrics["challenger"]["multiclass_log_loss"]
    improvement = (market_loss - challenger_loss) / market_loss
    brier_difference = (
        metrics["challenger"]["multiclass_brier_score"]
        - metrics["market"]["multiclass_brier_score"]
    )
    invalid = sum(
        abs(math.fsum(model["probabilities"]) - 1.0) > 1e-9
        for row in scores
        for model in row["models"].values()
    )
    thresholds = config["validation_gate"]
    diagnostics = {
        "event_count": len(scores),
        "date_cluster_count": len({row["target_date"] for row in scores}),
        "challenger_log_loss_improvement_fraction": improvement,
        "challenger_minus_market_brier": brier_difference,
        "invalid_probability_vector_count": invalid,
        "models": metrics,
    }
    checks = {
        "minimum_date_clusters": diagnostics["date_cluster_count"]
        >= thresholds["minimum_date_clusters"],
        "minimum_challenger_log_loss_improvement_fraction": improvement
        >= thresholds["minimum_challenger_log_loss_improvement_fraction"],
        "maximum_challenger_minus_market_brier": brier_difference
        <= thresholds["maximum_challenger_minus_market_brier"],
        "maximum_invalid_probability_vector_count": invalid
        <= thresholds["maximum_invalid_probability_vector_count"],
    }
    return diagnostics, checks


def uncertainty(scores: list[dict], config: dict) -> dict:
    left = [row["models"]["challenger"]["metrics"]["multiclass_log_loss"] for row in scores]
    right = [row["models"]["market"]["metrics"]["multiclass_log_loss"] for row in scores]
    return paired_cluster_bootstrap_mean_difference(
        left,
        right,
        [row["target_date"] for row in scores],
        10000,
        20260908,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_path = Path(config["source_dataset"])
    if sha256_path(source_path) != config["source_dataset_sha256"]:
        raise ValueError("source dataset checksum mismatch")
    source_rows = [json.loads(line) for line in source_path.read_text().splitlines()]
    rows = [
        row
        for row in source_rows
        if row["price_eligibility"] == config["eligibility"]["required_price_status"]
    ]
    split = config["temporal_split"]
    groups = {
        name: [row for row in rows if row["target_date"] in set(split[f"{name}_dates"])]
        for name in ("development", "validation", "test")
    }
    for name, expected in split["expected_counts"].items():
        if len(groups[name]) != expected:
            raise ValueError(f"{name} count changed")
    calibration_events = [model_event(row) for row in groups["development"]]
    grid = config["calibration_grid"]
    shifts = list(
        range(
            grid["shift_f"]["minimum"],
            grid["shift_f"]["maximum"] + 1,
            grid["shift_f"]["step"],
        )
    )
    selected = select_parameters(
        calibration_events,
        quantile_probabilities,
        shifts,
        grid["spread_scale"],
        config["metrics"]["probability_floor"],
    )
    floor = config["metrics"]["probability_floor"]
    development_scores = score_rows(
        groups["development"], selected["shift_f"], selected["spread_scale"], floor
    )
    validation_scores = score_rows(
        groups["validation"], selected["shift_f"], selected["spread_scale"], floor
    )
    validation_metrics, validation_checks = gate(validation_scores, config)
    validation_passed = all(validation_checks.values())
    test_scores = []
    test_metrics = None
    test_checks = None
    test_uncertainty = None
    if validation_passed:
        test_scores = score_rows(
            groups["test"], selected["shift_f"], selected["spread_scale"], floor
        )
        test_metrics, test_checks = gate(test_scores, config)
        test_uncertainty = uncertainty(test_scores, config)
    decision = (
        "VALIDATION_REJECT_TEST_UNTOUCHED"
        if not validation_passed
        else "TEST_PASS"
        if all(test_checks.values())
        else "TEST_REJECT"
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "source_dataset_sha256": sha256_path(source_path),
        "split_counts": {name: len(values) for name, values in groups.items()},
        "selected_calibration": selected,
        "development_metrics": aggregate(development_scores),
        "validation": {
            "metrics": validation_metrics,
            "checks": validation_checks,
            "uncertainty": uncertainty(validation_scores, config),
        },
        "test": {
            "consumed": validation_passed,
            "metrics": test_metrics,
            "checks": test_checks,
            "uncertainty": test_uncertainty,
        },
        "decision": decision,
        "boundary": config["boundary"],
    }
    args.output.mkdir(parents=True)
    (args.output / "validation-scores.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in validation_scores)
    )
    if test_scores:
        (args.output / "test-scores.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in test_scores)
        )
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if decision == "TEST_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
