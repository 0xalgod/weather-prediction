#!/usr/bin/env python3
"""Run preregistered expanding-window bias/spread calibration for KORD NBM."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.score_kord_annual_baselines import gaussian_vector, integer_celsius_buckets
from weather_quant.backtest.scoring import (
    mean_metrics,
    paired_bootstrap_mean_difference,
    score_probabilities,
)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inclusive_grid(minimum: float, maximum: float, step: float) -> list[float]:
    count = round((maximum - minimum) / step)
    values = [round(minimum + index * step, 10) for index in range(count + 1)]
    if step <= 0 or maximum < minimum or not math.isclose(values[-1], maximum):
        raise ValueError("invalid grid")
    return values


def select_candidate(candidates: list[dict], cumulative_losses: list[float], count: int) -> int:
    return min(
        range(len(candidates)),
        key=lambda index: (
            cumulative_losses[index] / count,
            abs(candidates[index]["shift_f"]),
            abs(candidates[index]["spread_scale"] - 1),
            candidates[index]["shift_f"],
            candidates[index]["spread_scale"],
        ),
    )


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
    grid = config["calibration_grid"]
    shifts = inclusive_grid(
        grid["temperature_shift_f_minimum"],
        grid["temperature_shift_f_maximum"],
        grid["temperature_shift_f_step"],
    )
    scales = inclusive_grid(
        grid["spread_scale_minimum"],
        grid["spread_scale_maximum"],
        grid["spread_scale_step"],
    )
    candidates = [
        {"shift_f": shift, "spread_scale": scale} for shift in shifts for scale in scales
    ]
    bins = config["outcome_bins_c"]
    buckets = integer_celsius_buckets(bins["minimum_integer"], bins["maximum_integer"])
    floor = config["metrics"]["probability_floor"]
    spread_floor = config["reference_model"]["standard_deviation_floor_f"]
    labels = [round((row["daily_maximum_dry_bulb_f"] - 32) * 5 / 9) for row in rows]
    winner_indices = [value - bins["minimum_integer"] for value in labels]

    candidate_losses = []
    for row, winner in zip(rows, winner_indices):
        base_spread = max(row["nbm_standard_deviation_f"], spread_floor)
        losses = []
        for candidate in candidates:
            probabilities = gaussian_vector(
                buckets,
                row["nbm_mean_f"] + candidate["shift_f"],
                base_spread * candidate["spread_scale"],
            )
            losses.append(-math.log(max(probabilities[winner], floor)))
        candidate_losses.append(losses)

    initial = config["walk_forward"]["initial_train_events"]
    cumulative = [
        math.fsum(candidate_losses[index][j] for index in range(initial))
        for j in range(len(candidates))
    ]
    events = []
    for index in range(initial, len(rows)):
        selected_index = select_candidate(candidates, cumulative, index)
        selected = candidates[selected_index]
        row = rows[index]
        base_spread = max(row["nbm_standard_deviation_f"], spread_floor)
        raw = gaussian_vector(buckets, row["nbm_mean_f"], base_spread)
        calibrated = gaussian_vector(
            buckets,
            row["nbm_mean_f"] + selected["shift_f"],
            base_spread * selected["spread_scale"],
        )
        events.append(
            {
                "target_date": row["target_date"],
                "train_event_count": index,
                "label_integer_c": labels[index],
                "selected_parameters": {
                    **selected,
                    "past_mean_log_loss": cumulative[selected_index] / index,
                },
                "slice_values": {
                    "nbm_version": row["nbm_version"],
                    "gefs_exact_partition": row["gefs_exact_partition"],
                    "month": date.fromisoformat(row["target_date"]).month,
                },
                "raw": score_probabilities(raw, winner_indices[index], floor),
                "calibrated": score_probabilities(calibrated, winner_indices[index], floor),
            }
        )
        for candidate_index, loss in enumerate(candidate_losses[index]):
            cumulative[candidate_index] += loss

    raw_metrics = mean_metrics([row["raw"] for row in events])
    calibrated_metrics = mean_metrics([row["calibrated"] for row in events])
    difference = paired_bootstrap_mean_difference(
        [row["calibrated"]["multiclass_log_loss"] for row in events],
        [row["raw"]["multiclass_log_loss"] for row in events],
        config["metrics"]["paired_date_bootstrap_repetitions"],
        config["metrics"]["paired_date_bootstrap_seed"],
    )
    relative = (
        raw_metrics["multiclass_log_loss"] - calibrated_metrics["multiclass_log_loss"]
    ) / raw_metrics["multiclass_log_loss"]
    brier_difference = (
        calibrated_metrics["multiclass_brier_score"] - raw_metrics["multiclass_brier_score"]
    )
    thresholds = config["acceptance_thresholds"]
    practical = (
        relative >= thresholds["relative_log_loss_improvement_minimum"]
        and brier_difference <= thresholds["brier_difference_maximum"]
    )
    strong = practical and difference["ci95_upper"] < thresholds["strong_evidence_ci95_upper_below"]
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "quality": {
            "development_event_count": len(rows),
            "oos_event_count": len(events),
            "candidate_count": len(candidates),
            "passed": len(events) == thresholds["exact_oos_event_count"],
        },
        "raw_oos_metrics": raw_metrics,
        "calibrated_oos_metrics": calibrated_metrics,
        "relative_log_loss_improvement": relative,
        "brier_difference": brier_difference,
        "calibrated_minus_raw_log_loss_bootstrap": difference,
        "practical_improvement_pass": practical,
        "strong_evidence_pass": strong,
        "decision": "STRONG_CALIBRATION_EVIDENCE" if strong else "NO_STRONG_CALIBRATION_EVIDENCE",
        "parameter_selection_counts": dict(
            Counter(
                "shift={shift_f},scale={spread_scale}".format(**row["selected_parameters"])
                for row in events
            )
        ),
        "trading_authorized": False,
        "events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console_result = {
        key: value
        for key, value in result.items()
        if key not in {"events", "parameter_selection_counts"}
    }
    print(json.dumps(console_result, indent=2))
    if not result["quality"]["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
