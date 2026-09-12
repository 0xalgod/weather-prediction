#!/usr/bin/env python3
"""Run the preregistered daily expanding-window KORD temperature forecast."""

from __future__ import annotations

import argparse
import json
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.run_kord_hourly_nextday_model import build_features, metrics, model, read_jsonl


def score_rows(rows: list[dict]) -> dict:
    """Score every registered predictor on a set of prediction rows."""
    actual = np.array([row["actual_c"] for row in rows], dtype=float)
    output = {"events": len(rows)}
    for name in ("expanding_ridge", "static_ridge", "persistence", "harmonic_climatology"):
        output[name] = metrics(actual, np.array([row[f"{name}_c"] for row in rows]))
    persistence_mae = output["persistence"]["mae_c"]
    output["mae_improvement_vs_persistence"] = (
        persistence_mae - output["expanding_ridge"]["mae_c"]
    ) / persistence_mae
    static_mae = output["static_ridge"]["mae_c"]
    output["mae_improvement_vs_static_ridge"] = (
        static_mae - output["expanding_ridge"]["mae_c"]
    ) / static_mae
    return output


def evaluate_gates(score: dict, thresholds: dict) -> dict[str, bool]:
    return {
        "minimum_mae_improvement_vs_persistence": score[
            "mae_improvement_vs_persistence"
        ]
        >= thresholds["minimum_mae_improvement_vs_persistence"],
        "maximum_absolute_bias_c": abs(score["expanding_ridge"]["bias_c"])
        <= thresholds["maximum_absolute_bias_c"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    hourly_path = Path(config["source_hourly"])
    labels_path = Path(config["source_labels"])
    static_result_path = Path(config["source_static_result"])
    expected_hashes = (
        (hourly_path, config["source_hourly_sha256"]),
        (labels_path, config["source_labels_sha256"]),
        (static_result_path, config["source_static_result_sha256"]),
    )
    for path, expected in expected_hashes:
        if sha256_path(path) != expected:
            raise ValueError(f"source checksum mismatch: {path}")

    feature_names, all_rows = build_features(read_jsonl(hourly_path), read_jsonl(labels_path))
    minimum_hours = config["eligibility"][
        "minimum_distinct_temperature_hours_through_18_lst"
    ]
    eligible = [row for row in all_rows if row["features"]["hour_count"] >= minimum_hours]
    train_bounds = config["initial_training_period"]
    evaluation_bounds = config["evaluation_period"]
    initial = [row for row in eligible if train_bounds[0] <= row["target_date"] <= train_bounds[1]]
    evaluation = [
        row
        for row in eligible
        if evaluation_bounds[0] <= row["target_date"] <= evaluation_bounds[1]
    ]
    expected = config["expected_counts"]
    if len(initial) != expected["initial_training"] or len(evaluation) != expected["evaluation"]:
        raise ValueError("initial/evaluation count mismatch")

    def xy(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.array([[row["features"][name] for name in feature_names] for row in rows]),
            np.array([row["target_c"] for row in rows]),
        )

    locked_spec = {"family": config["model"]["family"], "alpha": config["model"]["alpha"]}
    xinitial, yinitial = xy(initial)
    static_ridge = model(locked_spec).fit(xinitial, yinitial)
    history = list(initial)
    prediction_rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for row in evaluation:
            xhistory, yhistory = xy(history)
            xcurrent, _ = xy([row])
            expanding_ridge = model(locked_spec).fit(xhistory, yhistory)
            harmonic = LinearRegression().fit(xhistory[:, :2], yhistory)
            persistence = float(row["features"]["temp_max"])
            if not np.isfinite(persistence):
                persistence = float(harmonic.predict(xcurrent[:, :2])[0])
            prediction_rows.append(
                {
                    "target_date": row["target_date"],
                    "actual_c": float(row["target_c"]),
                    "training_count": len(history),
                    "expanding_ridge_c": float(expanding_ridge.predict(xcurrent)[0]),
                    "static_ridge_c": float(static_ridge.predict(xcurrent)[0]),
                    "persistence_c": persistence,
                    "harmonic_climatology_c": float(harmonic.predict(xcurrent[:, :2])[0]),
                }
            )
            history.append(row)

    segments = {
        name: [
            row
            for row in prediction_rows
            if bounds[0] <= row["target_date"] <= bounds[1]
        ]
        for name, bounds in config["evaluation_segments"].items()
    }
    if any(len(segments[name]) != expected[name] for name in segments):
        raise ValueError("evaluation segment count mismatch")
    scores = {"full_evaluation": score_rows(prediction_rows)}
    scores.update({name: score_rows(rows) for name, rows in segments.items()})
    monthly_rows: dict[str, list[dict]] = defaultdict(list)
    for row in prediction_rows:
        monthly_rows[row["target_date"][:7]].append(row)
    monthly = {month: score_rows(rows) for month, rows in sorted(monthly_rows.items())}
    gate_checks = {
        name: evaluate_gates(scores[name], thresholds)
        for name, thresholds in config["exploratory_gates"].items()
    }
    passed = all(all(checks.values()) for checks in gate_checks.values())

    args.output.mkdir(parents=True)
    prediction_path = args.output / "predictions.jsonl"
    prediction_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in prediction_rows)
    )
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "feature_count": len(feature_names),
        "counts": {
            "initial_training": len(initial),
            "evaluation": len(evaluation),
            **{name: len(rows) for name, rows in segments.items()},
        },
        "scores": scores,
        "monthly": monthly,
        "gate_checks": gate_checks,
        "decision": (
            "EXPLORATORY_PASS_REQUIRES_NEW_CONFIRMATION"
            if passed
            else "EXPLORATORY_REJECT"
        ),
        "predictions_sha256": sha256_path(prediction_path),
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
