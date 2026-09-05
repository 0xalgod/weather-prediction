#!/usr/bin/env python3
"""Run the pre-registered Chicago expanding-window calibration experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from weather_quant.backtest.scoring import paired_bootstrap_mean_difference
from weather_quant.forecasting.calibration import (
    aggregate_event_scores,
    event_model_score,
    gaussian_probabilities,
    quantile_probabilities,
    select_parameters,
    shift_grid,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"immutable output exists: {args.output}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source_path = Path(config["source"])
    if sha256_path(source_path) != config["source_sha256"]:
        raise ValueError("source dataset checksum mismatch")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    minimum_date = date.fromisoformat(config["eligibility"]["target_date_minimum"])
    events = sorted(
        (
            row
            for row in source["rows"]
            if row["eligible"] and date.fromisoformat(row["target_local_date"]) >= minimum_date
        ),
        key=lambda row: row["target_local_date"],
    )
    if len(events) != config["eligibility"]["expected_eligible_events"]:
        raise ValueError(f"expected 112 eligible events, found {len(events)}")
    observed_dates = {row["target_local_date"] for row in events}
    if any(value in observed_dates for value in config["eligibility"]["known_missing_dates"]):
        raise ValueError("known missing date unexpectedly entered the sample")

    grid = config["calibration_grid"]
    shifts = shift_grid(
        grid["temperature_shift_f_minimum"],
        grid["temperature_shift_f_maximum"],
        grid["temperature_shift_f_step"],
    )
    scales = grid["spread_scale"]
    floor = config["metrics"]["probability_floor"]
    initial_train = config["walk_forward"]["initial_train_events"]
    model_functions = {
        "gaussian": gaussian_probabilities,
        "quantile": quantile_probabilities,
    }
    oos_rows = []
    for event_index in range(initial_train, len(events)):
        train_events = events[:event_index]
        test_event = events[event_index]
        models = {}
        for model_name, probability_function in model_functions.items():
            selected = select_parameters(train_events, probability_function, shifts, scales, floor)
            models[model_name] = {
                "selected_parameters": selected,
                "raw": event_model_score(test_event, probability_function, 0.0, 1.0, floor),
                "calibrated": event_model_score(
                    test_event,
                    probability_function,
                    selected["shift_f"],
                    selected["spread_scale"],
                    floor,
                ),
            }
        oos_rows.append(
            {
                "event_id": test_event["event_id"],
                "target_local_date": test_event["target_local_date"],
                "train_event_count": len(train_events),
                "winning_bucket_label": test_event["winning_bucket_label"],
                "models": models,
            }
        )

    expected_oos = config["walk_forward"]["expected_oos_events"]
    if len(oos_rows) != expected_oos:
        raise ValueError(f"expected {expected_oos} OOS rows, found {len(oos_rows)}")
    repetitions = config["metrics"]["paired_bootstrap_repetitions"]
    seed = config["metrics"]["paired_bootstrap_seed"]
    thresholds = config["acceptance_thresholds"]
    model_results = {}
    for model_name in model_functions:
        raw_scores = [row["models"][model_name]["raw"] for row in oos_rows]
        calibrated_scores = [row["models"][model_name]["calibrated"] for row in oos_rows]
        raw_aggregate = aggregate_event_scores(raw_scores)
        calibrated_aggregate = aggregate_event_scores(calibrated_scores)
        log_loss_difference = paired_bootstrap_mean_difference(
            [score["metrics"]["multiclass_log_loss"] for score in calibrated_scores],
            [score["metrics"]["multiclass_log_loss"] for score in raw_scores],
            repetitions,
            seed,
        )
        relative_improvement = (
            raw_aggregate["multiclass_log_loss"] - calibrated_aggregate["multiclass_log_loss"]
        ) / raw_aggregate["multiclass_log_loss"]
        brier_difference = (
            calibrated_aggregate["multiclass_brier_score"] - raw_aggregate["multiclass_brier_score"]
        )
        practical_pass = (
            relative_improvement >= thresholds["relative_log_loss_improvement_minimum"]
            and brier_difference <= thresholds["brier_difference_maximum"]
        )
        strong_pass = (
            practical_pass
            and log_loss_difference["ci95_upper"] < thresholds["strong_evidence_ci95_upper_below"]
        )
        model_results[model_name] = {
            "raw_oos_metrics": raw_aggregate,
            "calibrated_oos_metrics": calibrated_aggregate,
            "relative_log_loss_improvement": relative_improvement,
            "brier_difference": brier_difference,
            "calibrated_minus_raw_log_loss_bootstrap": log_loss_difference,
            "practical_improvement_pass": practical_pass,
            "strong_evidence_pass": strong_pass,
        }

    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config": config,
        "quality": {
            "eligible_event_count": len(events),
            "initial_train_event_count": initial_train,
            "oos_event_count": len(oos_rows),
            "first_oos_date": oos_rows[0]["target_local_date"],
            "last_oos_date": oos_rows[-1]["target_local_date"],
        },
        "model_results": model_results,
        "decision": (
            "STRONG_CALIBRATION_EVIDENCE"
            if any(row["strong_evidence_pass"] for row in model_results.values())
            else "NO_STRONG_CALIBRATION_EVIDENCE"
        ),
        "oos_rows": oos_rows,
        "trading_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "oos_rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
