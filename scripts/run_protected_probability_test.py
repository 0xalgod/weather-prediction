#!/usr/bin/env python3
"""Generate protected points and run the frozen probability test exactly once."""

from __future__ import annotations

import argparse
import json
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import norm
from sklearn.linear_model import LinearRegression

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.run_kord_hourly_nextday_model import build_features, model, read_jsonl
from scripts.select_probability_candidate import c_to_f, score_samples


def development_baseline_samples(selection_config: dict) -> tuple[np.ndarray, np.ndarray]:
    persistence_errors = []
    harmonic_errors = []
    for source in selection_config["development_predictions"]:
        path = Path(source["path"])
        if sha256_path(path) != source["sha256"]:
            raise ValueError(f"development source checksum mismatch: {path}")
        for row in read_jsonl(path):
            actual = c_to_f(row["actual_c"])
            persistence_errors.append(actual - c_to_f(row["persistence_c"]))
            harmonic_errors.append(actual - c_to_f(row["harmonic_climatology_c"]))
    count = selection_config["distribution_numerics"]["deterministic_sample_count"]
    probabilities = np.arange(1, count + 1) / (count + 1)
    persistence_errors = np.array(persistence_errors)
    persistence_samples = float(np.mean(persistence_errors)) + float(
        np.std(persistence_errors)
    ) * norm.ppf(probabilities)
    harmonic_samples = np.quantile(np.array(harmonic_errors), probabilities)
    return persistence_samples, harmonic_samples


def centered_rows(rows: list[dict], point_field: str) -> list[dict]:
    return [{**row, "point_f": row[point_field]} for row in rows]


def pit_diagnostic(rows: list[dict], residual_sample: np.ndarray) -> dict:
    pits = np.array(
        [
            np.mean(row["point_f"] + residual_sample <= row["actual_f"])
            for row in rows
        ]
    )
    counts, _ = np.histogram(pits, bins=np.linspace(0, 1, 11))
    frequencies = counts / counts.sum()
    return {
        "mean_pit": float(np.mean(pits)),
        "ten_bin_counts": counts.tolist(),
        "ten_bin_frequencies": frequencies.tolist(),
        "ece_total_variation_from_uniform": float(0.5 * np.sum(np.abs(frequencies - 0.1))),
    }


def date_cluster_bootstrap(
    candidate_details: list[dict], baseline_details: list[dict], resamples: int, seed: int
) -> dict:
    by_date: dict[str, list[float]] = defaultdict(list)
    for candidate, baseline in zip(candidate_details, baseline_details):
        if (
            candidate["station"] != baseline["station"]
            or candidate["target_date"] != baseline["target_date"]
        ):
            raise ValueError("paired probability score rows are misaligned")
        by_date[candidate["target_date"]].append(
            baseline["crps_f"] - candidate["crps_f"]
        )
    dates = sorted(by_date)
    sums = np.array([sum(by_date[target_date]) for target_date in dates])
    counts = np.array([len(by_date[target_date]) for target_date in dates])
    rng = np.random.default_rng(seed)
    estimates = np.empty(resamples)
    for index in range(resamples):
        sampled = rng.integers(0, len(dates), len(dates))
        estimates[index] = sums[sampled].sum() / counts[sampled].sum()
    return {
        "cluster_count": len(dates),
        "resamples": resamples,
        "seed": seed,
        "mean_crps_reduction_f": float(sums.sum() / counts.sum()),
        "lower_95pct_f": float(np.quantile(estimates, 0.025)),
        "upper_95pct_f": float(np.quantile(estimates, 0.975)),
    }


def gate_checks(
    candidate: dict,
    persistence: dict,
    harmonic: dict,
    bootstrap: dict,
    station_scores: dict,
    gates: dict,
) -> tuple[dict, dict]:
    best_crps_name, best_crps = min(
        (("persistence_gaussian", persistence), ("harmonic_empirical", harmonic)),
        key=lambda item: item[1]["mean_crps_f"],
    )
    best_log_name, best_log = min(
        (("persistence_gaussian", persistence), ("harmonic_empirical", harmonic)),
        key=lambda item: item[1]["categorical_log_loss"],
    )
    crps_improvement = (
        best_crps["mean_crps_f"] - candidate["mean_crps_f"]
    ) / best_crps["mean_crps_f"]
    log_improvement = (
        best_log["categorical_log_loss"] - candidate["categorical_log_loss"]
    ) / best_log["categorical_log_loss"]
    positive_stations = sum(
        scores["candidate"]["mean_crps_f"]
        < min(
            scores["persistence_gaussian"]["mean_crps_f"],
            scores["harmonic_empirical"]["mean_crps_f"],
        )
        for scores in station_scores.values()
    )
    comparisons = {
        "best_crps_baseline": best_crps_name,
        "best_log_loss_baseline": best_log_name,
        "pooled_crps_improvement_vs_best_baseline": crps_improvement,
        "pooled_log_loss_improvement_vs_best_baseline": log_improvement,
        "protected_stations_with_positive_crps_improvement": positive_stations,
    }
    checks = {
        "minimum_pooled_crps_improvement_vs_best_baseline": crps_improvement
        >= gates["minimum_pooled_crps_improvement_vs_best_baseline"],
        "minimum_pooled_log_loss_improvement_vs_best_baseline": log_improvement
        >= gates["minimum_pooled_log_loss_improvement_vs_best_baseline"],
        "minimum_target_date_cluster_bootstrap_95pct_lower_bound_crps_reduction_f": bootstrap[
            "lower_95pct_f"
        ]
        > gates[
            "minimum_target_date_cluster_bootstrap_95pct_lower_bound_crps_reduction_f"
        ],
        "minimum_80pct_interval_coverage": candidate["coverage80"]
        >= gates["minimum_80pct_interval_coverage"],
        "maximum_80pct_interval_coverage": candidate["coverage80"]
        <= gates["maximum_80pct_interval_coverage"],
        "minimum_90pct_interval_coverage": candidate["coverage90"]
        >= gates["minimum_90pct_interval_coverage"],
        "maximum_90pct_interval_coverage": candidate["coverage90"]
        <= gates["maximum_90pct_interval_coverage"],
        "minimum_protected_stations_with_positive_crps_improvement": positive_stations
        >= gates["minimum_protected_stations_with_positive_crps_improvement"],
    }
    return comparisons, checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_keys = (
        ("probability_design", "probability_design_sha256"),
        ("candidate_selection_result", "candidate_selection_result_sha256"),
        ("candidate_selection_config", "candidate_selection_config_sha256"),
        ("frozen_candidate_artifact", "frozen_candidate_artifact_sha256"),
        ("protected_dataset_result", "protected_dataset_result_sha256"),
    )
    for path_key, hash_key in source_keys:
        if sha256_path(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"source checksum mismatch: {path_key}")
    design = json.loads(Path(config["probability_design"]).read_text())
    selection_result = json.loads(Path(config["candidate_selection_result"]).read_text())
    selection_config = json.loads(Path(config["candidate_selection_config"]).read_text())
    candidate_artifact = json.loads(Path(config["frozen_candidate_artifact"]).read_text())
    dataset = json.loads(Path(config["protected_dataset_result"]).read_text())
    if selection_result["decision"] != "DEVELOPMENT_CANDIDATE_FROZEN":
        raise ValueError("probability candidate is not frozen")
    if dataset["decision"] != "MULTICITY_DATA_QUALITY_PASS":
        raise ValueError("protected dataset quality did not pass")
    candidate_residual_sample = np.array(candidate_artifact["residual_sample_f"])
    persistence_sample, harmonic_sample = development_baseline_samples(selection_config)
    train_bounds = config["protected_point_generation"]["initial_history"]
    evaluation_bounds = config["protected_point_generation"]["single_use_evaluation"]
    station_predictions = []
    counts = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for station in design["protected_test_stations"]:
            icao = station["icao"]
            artifacts = dataset["stations"][icao]["artifacts"]
            hourly_path = Path(artifacts["hourly"])
            labels_path = Path(artifacts["labels"])
            if sha256_path(hourly_path) != artifacts["hourly_sha256"]:
                raise ValueError(f"hourly checksum mismatch: {icao}")
            if sha256_path(labels_path) != artifacts["labels_sha256"]:
                raise ValueError(f"labels checksum mismatch: {icao}")
            names, rows = build_features(read_jsonl(hourly_path), read_jsonl(labels_path))
            eligible = [
                row
                for row in rows
                if row["target_c"] is not None and row["features"]["hour_count"] >= 18
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
                raise ValueError(f"protected segment eligibility below 95%: {icao}")

            def xy(selected: list[dict], feature_names: tuple[str, ...] = tuple(names)):
                return (
                    np.array(
                        [
                            [row["features"][name] for name in feature_names]
                            for row in selected
                        ]
                    ),
                    np.array([row["target_c"] for row in selected]),
                )

            history = list(initial)
            for row in evaluation:
                xhistory, yhistory = xy(history)
                xcurrent, _ = xy([row])
                fitted = model({"family": "ridge", "alpha": 100.0}).fit(xhistory, yhistory)
                harmonic = LinearRegression().fit(xhistory[:, :2], yhistory)
                persistence_c = float(row["features"]["temp_max"])
                if not np.isfinite(persistence_c):
                    persistence_c = float(harmonic.predict(xcurrent[:, :2])[0])
                station_predictions.append(
                    {
                        "station": icao,
                        "target_date": row["target_date"],
                        "actual_f": c_to_f(float(row["target_c"])),
                        "point_f": c_to_f(float(fitted.predict(xcurrent)[0])),
                        "persistence_f": c_to_f(persistence_c),
                        "harmonic_f": c_to_f(float(harmonic.predict(xcurrent[:, :2])[0])),
                        "training_count": len(history),
                    }
                )
                history.append(row)
            counts[icao] = {
                "initial_training": len(initial),
                "evaluation": len(evaluation),
                "no_score_total": len(rows) - len(eligible),
            }
    count = len(station_predictions)
    candidate_score, candidate_details = score_samples(
        station_predictions,
        np.tile(candidate_residual_sample, (count, 1)),
        1e-6,
    )
    persistence_rows = centered_rows(station_predictions, "persistence_f")
    persistence_score, persistence_details = score_samples(
        persistence_rows, np.tile(persistence_sample, (count, 1)), 1e-6
    )
    harmonic_rows = centered_rows(station_predictions, "harmonic_f")
    harmonic_score, harmonic_details = score_samples(
        harmonic_rows, np.tile(harmonic_sample, (count, 1)), 1e-6
    )
    station_scores = {}
    for station in config["protected_point_generation"]["stations"]:
        indices = [
            index for index, row in enumerate(station_predictions) if row["station"] == station
        ]
        station_scores[station] = {
            "candidate": score_samples(
                [station_predictions[index] for index in indices],
                np.tile(candidate_residual_sample, (len(indices), 1)),
                1e-6,
            )[0],
            "persistence_gaussian": score_samples(
                [persistence_rows[index] for index in indices],
                np.tile(persistence_sample, (len(indices), 1)),
                1e-6,
            )[0],
            "harmonic_empirical": score_samples(
                [harmonic_rows[index] for index in indices],
                np.tile(harmonic_sample, (len(indices), 1)),
                1e-6,
            )[0],
        }
    if persistence_score["mean_crps_f"] <= harmonic_score["mean_crps_f"]:
        bootstrap_baseline_details = persistence_details
    else:
        bootstrap_baseline_details = harmonic_details
    bootstrap = date_cluster_bootstrap(
        candidate_details,
        bootstrap_baseline_details,
        config["bootstrap"]["resamples"],
        config["bootstrap"]["seed"],
    )
    comparisons, checks = gate_checks(
        candidate_score,
        persistence_score,
        harmonic_score,
        bootstrap,
        station_scores,
        config["gates_inherited_without_change"],
    )
    pit = pit_diagnostic(station_predictions, candidate_residual_sample)
    passed = all(checks.values())
    args.output.mkdir(parents=True)
    predictions_path = args.output / "protected_point_predictions.jsonl"
    predictions_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in station_predictions)
    )
    score_rows = []
    for index, row in enumerate(station_predictions):
        score_rows.append(
            {
                "station": row["station"],
                "target_date": row["target_date"],
                "candidate": candidate_details[index],
                "persistence_gaussian": persistence_details[index],
                "harmonic_empirical": harmonic_details[index],
            }
        )
    scores_path = args.output / "protected_probability_scores.jsonl"
    scores_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in score_rows)
    )
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "counts": counts,
        "pooled_scores": {
            "candidate": candidate_score,
            "persistence_gaussian": persistence_score,
            "harmonic_empirical": harmonic_score,
        },
        "station_scores": station_scores,
        "comparisons": comparisons,
        "date_cluster_bootstrap": bootstrap,
        "pit_diagnostic": pit,
        "checks": checks,
        "decision": "PROTECTED_PROBABILITY_PASS" if passed else "PROTECTED_PROBABILITY_FAIL",
        "artifacts": {
            "point_predictions_sha256": sha256_path(predictions_path),
            "probability_scores_sha256": sha256_path(scores_path),
        },
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
