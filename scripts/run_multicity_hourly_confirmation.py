#!/usr/bin/env python3
"""Run the frozen five-station expanding-window confirmation once."""

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


def score_predictions(rows: list[dict]) -> dict:
    actual = np.array([row["actual_c"] for row in rows], dtype=float)
    expanding = np.array([row["expanding_ridge_c"] for row in rows], dtype=float)
    persistence = np.array([row["persistence_c"] for row in rows], dtype=float)
    harmonic = np.array([row["harmonic_climatology_c"] for row in rows], dtype=float)
    expanding_metrics = metrics(actual, expanding)
    persistence_metrics = metrics(actual, persistence)
    return {
        "events": len(rows),
        "expanding_ridge": expanding_metrics,
        "persistence": persistence_metrics,
        "harmonic_climatology": metrics(actual, harmonic),
        "mae_improvement_vs_persistence": (
            persistence_metrics["mae_c"] - expanding_metrics["mae_c"]
        )
        / persistence_metrics["mae_c"],
        "paired_mae_reduction_c": persistence_metrics["mae_c"]
        - expanding_metrics["mae_c"],
    }


def date_cluster_bootstrap(
    rows: list[dict], resamples: int, seed: int
) -> dict[str, float | int]:
    by_date: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        model_error = abs(row["expanding_ridge_c"] - row["actual_c"])
        persistence_error = abs(row["persistence_c"] - row["actual_c"])
        by_date[row["target_date"]].append(persistence_error - model_error)
    dates = sorted(by_date)
    cluster_sums = np.array([sum(by_date[target_date]) for target_date in dates])
    cluster_counts = np.array([len(by_date[target_date]) for target_date in dates])
    rng = np.random.default_rng(seed)
    estimates = np.empty(resamples)
    for index in range(resamples):
        sampled = rng.integers(0, len(dates), len(dates))
        estimates[index] = cluster_sums[sampled].sum() / cluster_counts[sampled].sum()
    return {
        "cluster_count": len(dates),
        "resamples": resamples,
        "seed": seed,
        "mean_paired_mae_reduction_c": float(cluster_sums.sum() / cluster_counts.sum()),
        "lower_95pct_c": float(np.quantile(estimates, 0.025)),
        "upper_95pct_c": float(np.quantile(estimates, 0.975)),
    }


def confirmation_checks(
    pooled: dict, station_scores: dict[str, dict], bootstrap: dict, gates: dict
) -> dict[str, bool]:
    positive_stations = sum(
        score["mae_improvement_vs_persistence"] > 0 for score in station_scores.values()
    )
    strict_stations = sum(
        score["mae_improvement_vs_persistence"] >= 0.05
        and abs(score["expanding_ridge"]["bias_c"]) <= 1.0
        for score in station_scores.values()
    )
    return {
        "minimum_pooled_mae_improvement_vs_persistence": pooled[
            "mae_improvement_vs_persistence"
        ]
        >= gates["minimum_pooled_mae_improvement_vs_persistence"],
        "maximum_pooled_absolute_bias_c": abs(pooled["expanding_ridge"]["bias_c"])
        <= gates["maximum_pooled_absolute_bias_c"],
        "minimum_date_cluster_bootstrap_95pct_lower_bound_mae_reduction_c": bootstrap[
            "lower_95pct_c"
        ]
        > gates["minimum_date_cluster_bootstrap_95pct_lower_bound_mae_reduction_c"],
        "minimum_stations_with_positive_mae_improvement": positive_stations
        >= gates["minimum_stations_with_positive_mae_improvement"],
        "minimum_stations_meeting_5pct_skill_and_1c_bias": strict_stations
        >= gates["minimum_stations_meeting_5pct_skill_and_1c_bias"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    execution = json.loads(args.config.read_text())
    design_path = Path(execution["confirmation_design"])
    dataset_path = Path(execution["corrected_dataset_result"])
    if sha256_path(design_path) != execution["confirmation_design_sha256"]:
        raise ValueError("confirmation design checksum mismatch")
    if sha256_path(dataset_path) != execution["corrected_dataset_result_sha256"]:
        raise ValueError("corrected dataset checksum mismatch")
    design = json.loads(design_path.read_text())
    dataset = json.loads(dataset_path.read_text())
    if dataset["decision"] != "CORRECTED_DATASET_PASS":
        raise ValueError("corrected data-quality gate did not pass")

    train_bounds = design["window"]["initial_training_period"]
    evaluation_bounds = design["window"]["evaluation_period"]
    minimum_hours = 18
    locked_spec = design["frozen_forecasting_procedure"]["model"]
    model_spec = {"family": locked_spec["family"], "alpha": locked_spec["alpha"]}
    all_prediction_rows = []
    station_counts = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for station in design["stations"]:
            icao = station["icao"]
            source = dataset["stations"][icao]["artifacts"]
            hourly_path = Path(source["hourly"])
            labels_path = Path(source["labels"])
            if sha256_path(hourly_path) != source["hourly_sha256"]:
                raise ValueError(f"hourly checksum mismatch: {icao}")
            if sha256_path(labels_path) != source["labels_sha256"]:
                raise ValueError(f"labels checksum mismatch: {icao}")
            feature_names, rows = build_features(
                read_jsonl(hourly_path), read_jsonl(labels_path)
            )
            eligible = [
                row
                for row in rows
                if row["target_c"] is not None
                and row["features"]["hour_count"] >= minimum_hours
            ]
            initial = [
                row for row in eligible if train_bounds[0] <= row["target_date"] <= train_bounds[1]
            ]
            evaluation = [
                row
                for row in eligible
                if evaluation_bounds[0] <= row["target_date"] <= evaluation_bounds[1]
            ]
            if len(initial) < 0.95 * 365 or len(evaluation) < 0.95 * 365:
                raise ValueError(f"segment eligibility unexpectedly below 95%: {icao}")

            def xy(
                selected: list[dict], names: tuple[str, ...] = tuple(feature_names)
            ) -> tuple[np.ndarray, np.ndarray]:
                return (
                    np.array(
                        [
                            [row["features"][name] for name in names]
                            for row in selected
                        ]
                    ),
                    np.array([row["target_c"] for row in selected]),
                )

            history = list(initial)
            station_predictions = []
            for row in evaluation:
                xhistory, yhistory = xy(history)
                xcurrent, _ = xy([row])
                fitted = model(model_spec).fit(xhistory, yhistory)
                harmonic = LinearRegression().fit(xhistory[:, :2], yhistory)
                persistence = float(row["features"]["temp_max"])
                if not np.isfinite(persistence):
                    persistence = float(harmonic.predict(xcurrent[:, :2])[0])
                station_predictions.append(
                    {
                        "station": icao,
                        "target_date": row["target_date"],
                        "actual_c": float(row["target_c"]),
                        "training_count": len(history),
                        "expanding_ridge_c": float(fitted.predict(xcurrent)[0]),
                        "persistence_c": persistence,
                        "harmonic_climatology_c": float(
                            harmonic.predict(xcurrent[:, :2])[0]
                        ),
                    }
                )
                history.append(row)
            station_counts[icao] = {
                "initial_training": len(initial),
                "evaluation": len(evaluation),
                "no_score_total": len(rows) - len(eligible),
            }
            all_prediction_rows.extend(station_predictions)

    station_scores = {
        station["icao"]: score_predictions(
            [row for row in all_prediction_rows if row["station"] == station["icao"]]
        )
        for station in design["stations"]
    }
    pooled = score_predictions(all_prediction_rows)
    bootstrap = date_cluster_bootstrap(
        all_prediction_rows,
        design["bootstrap"]["resamples"],
        design["bootstrap"]["seed"],
    )
    checks = confirmation_checks(
        pooled, station_scores, bootstrap, design["confirmation_gates"]
    )
    passed = all(checks.values())
    args.output.mkdir(parents=True)
    predictions_path = args.output / "predictions.jsonl"
    predictions_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in all_prediction_rows)
    )
    result = {
        "experiment_id": execution["experiment_id"],
        "generated_at_utc": utc_now(),
        "execution_config_sha256": sha256_path(args.config),
        "confirmation_design_sha256": sha256_path(design_path),
        "corrected_dataset_result_sha256": sha256_path(dataset_path),
        "counts": station_counts,
        "station_scores": station_scores,
        "pooled_score": pooled,
        "date_cluster_bootstrap": bootstrap,
        "checks": checks,
        "decision": "CONFIRMATION_PASS" if passed else "CONFIRMATION_FAIL",
        "predictions_sha256": sha256_path(predictions_path),
        "boundary": execution["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
