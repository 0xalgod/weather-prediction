#!/usr/bin/env python3
"""Diagnose the locked KORD hourly model's validation/test drift without tuning."""

from __future__ import annotations

import argparse
import json
import math
import warnings
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.run_kord_hourly_nextday_model import build_features, metrics, model, read_jsonl


def aggregate_monthly(rows: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["target_date"][:7]].append(row)
    return {
        month: {
            "count": len(values),
            **metrics(
                np.array([row["actual_c"] for row in values]),
                np.array([row["prediction_c"] for row in values]),
            ),
        }
        for month, values in sorted(groups.items())
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_result = Path(config["source_model_result"])
    if sha256_path(source_result) != config["source_model_result_sha256"]:
        raise ValueError("source model result checksum mismatch")
    model_config = json.loads(Path(config["source_config"]).read_text())
    hourly = Path(model_config["source_hourly"])
    labels = Path(model_config["source_labels"])
    names, all_rows = build_features(read_jsonl(hourly), read_jsonl(labels))
    minimum_hours = model_config["eligibility"]["minimum_distinct_temperature_hours_through_18_lst"]
    eligible = [row for row in all_rows if row["features"]["hour_count"] >= minimum_hours]
    split = model_config["temporal_split"]
    groups = {
        name: [row for row in eligible if split[name][0] <= row["target_date"] <= split[name][1]]
        for name in ("train", "validation", "test")
    }

    def xy(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.array([[row["features"][name] for name in names] for row in rows]),
            np.array([row["target_c"] for row in rows]),
        )

    xtrain, ytrain = xy(groups["train"])
    fitted = model(config["locked_model"]).fit(xtrain, ytrain)
    residual_rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for split_name in ("validation", "test"):
            xvalues, yvalues = xy(groups[split_name])
            predictions = fitted.predict(xvalues)
            residual_rows.extend(
                {
                    "split": split_name,
                    "target_date": row["target_date"],
                    "actual_c": float(actual),
                    "prediction_c": float(prediction),
                    "error_c": float(prediction - actual),
                }
                for row, actual, prediction in zip(groups[split_name], yvalues, predictions)
            )
    monthly = {
        split_name: aggregate_monthly([row for row in residual_rows if row["split"] == split_name])
        for split_name in ("validation", "test")
    }
    test_rows = [row for row in residual_rows if row["split"] == "test"]
    rolling = []
    for row in test_rows:
        endpoint = date.fromisoformat(row["target_date"])
        start = endpoint - timedelta(days=29)
        window = [
            item
            for item in test_rows
            if start <= date.fromisoformat(item["target_date"]) <= endpoint
        ]
        if len(window) >= 25:
            rolling.append(
                {
                    "end_date": row["target_date"],
                    "count": len(window),
                    "bias_c": float(np.mean([item["error_c"] for item in window])),
                }
            )
    feature_shifts = []
    xtest, _ = xy(groups["test"])
    for index, name in enumerate(names):
        train_values = xtrain[:, index].astype(float)
        test_values = xtest[:, index].astype(float)
        train_values = train_values[np.isfinite(train_values)]
        test_values = test_values[np.isfinite(test_values)]
        scale = float(np.std(train_values)) if len(train_values) else math.nan
        shift = (
            float((np.mean(test_values) - np.mean(train_values)) / scale)
            if len(test_values) and scale > 0
            else None
        )
        feature_shifts.append({"feature": name, "standardized_mean_shift": shift})
    feature_shifts.sort(key=lambda row: abs(row["standardized_mean_shift"] or 0), reverse=True)
    threshold = config["classification_thresholds"]
    negative_months = [
        month for month, values in monthly["test"].items() if values["bias_c"] <= -1.0
    ]
    confirmed = (
        len(negative_months) >= threshold["minimum_test_months_with_bias_at_or_below_minus_1c"]
    )
    summary = {
        "test_month_count": len(monthly["test"]),
        "test_months_bias_at_or_below_minus_1c": negative_months,
        "negative_bias_month_count": len(negative_months),
        "minimum_30day_rolling_bias_c": min(row["bias_c"] for row in rolling),
        "maximum_30day_rolling_bias_c": max(row["bias_c"] for row in rolling),
        "material_feature_shift_count": sum(
            row["standardized_mean_shift"] is not None
            and abs(row["standardized_mean_shift"])
            >= threshold["material_feature_shift_absolute_standard_deviations"]
            for row in feature_shifts
        ),
        "top_feature_shifts": feature_shifts[:10],
    }
    args.output.mkdir(parents=True)
    residual_path = args.output / "residuals.jsonl"
    residual_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in residual_rows)
    )
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "source_model_result_sha256": sha256_path(source_result),
        "monthly": monthly,
        "summary": summary,
        "decision": "PERSISTENT_REGIME_DRIFT_CONFIRMED" if confirmed else "ISOLATED_ERROR_PATTERN",
        "residuals_sha256": sha256_path(residual_path),
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
