#!/usr/bin/env python3
"""Select and freeze a probability model using development stations only."""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

import joblib
import numpy as np
from scipy.stats import norm, t
from sklearn.ensemble import GradientBoostingRegressor

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from scripts.run_kord_hourly_nextday_model import read_jsonl


def c_to_f(value: float) -> float:
    return value * 9 / 5 + 32


def load_development_rows(config: dict) -> list[dict]:
    rows = []
    for source in config["development_predictions"]:
        path = Path(source["path"])
        if sha256_path(path) != source["sha256"]:
            raise ValueError(f"development prediction checksum mismatch: {path}")
        for raw in read_jsonl(path):
            target_date = date.fromisoformat(raw["target_date"])
            actual_f = c_to_f(raw["actual_c"])
            point_f = c_to_f(raw["expanding_ridge_c"])
            rows.append(
                {
                    "station": raw.get("station", source.get("station_default")),
                    "target_date": raw["target_date"],
                    "actual_f": actual_f,
                    "point_f": point_f,
                    "residual_f": actual_f - point_f,
                    "sin_doy": math.sin(2 * math.pi * target_date.timetuple().tm_yday / 365.25),
                    "cos_doy": math.cos(2 * math.pi * target_date.timetuple().tm_yday / 365.25),
                }
            )
    if any(row["station"] is None for row in rows):
        raise ValueError("missing development station identity")
    return rows


def feature_matrix(rows: list[dict], stations: list[str]) -> np.ndarray:
    return np.array(
        [
            [row["point_f"], row["sin_doy"], row["cos_doy"]]
            + [float(row["station"] == station) for station in stations]
            for row in rows
        ]
    )


def fit_quantile_gbt(
    train_rows: list[dict], stations: list[str], quantiles: list[float], spec: dict, seed: int
) -> list[GradientBoostingRegressor]:
    xtrain = feature_matrix(train_rows, stations)
    residuals = np.array([row["residual_f"] for row in train_rows])
    models = []
    for quantile in quantiles:
        fitted = GradientBoostingRegressor(
            loss="quantile",
            alpha=quantile,
            random_state=seed,
            **spec,
        ).fit(xtrain, residuals)
        models.append(fitted)
    return models


def residual_samples(
    family: str,
    spec: dict,
    train_rows: list[dict],
    test_rows: list[dict],
    stations: list[str],
    config: dict,
    fold_seed: int,
) -> np.ndarray:
    count = config["distribution_numerics"]["deterministic_sample_count"]
    probabilities = np.arange(1, count + 1) / (count + 1)
    residuals = np.array([row["residual_f"] for row in train_rows])
    if family == "gaussian_residual":
        base = float(np.mean(residuals)) + float(np.std(residuals)) * norm.ppf(probabilities)
        return np.tile(base, (len(test_rows), 1))
    if family == "student_t_residual":
        degrees = spec["degrees_of_freedom"]
        scale = float(np.std(residuals)) * math.sqrt((degrees - 2) / degrees)
        base = float(np.mean(residuals)) + scale * t.ppf(probabilities, degrees)
        return np.tile(base, (len(test_rows), 1))
    if family == "empirical_residual":
        base = np.quantile(residuals, probabilities)
        noise = norm.ppf(probabilities)
        rng = np.random.default_rng(fold_seed)
        rng.shuffle(noise)
        base = np.sort(base + spec["gaussian_jitter_bandwidth_f"] * noise)
        return np.tile(base, (len(test_rows), 1))
    if family != "quantile_gbt_residual":
        raise ValueError(f"unknown family: {family}")
    quantiles = config["candidates"][family]["quantiles"]
    models = fit_quantile_gbt(
        train_rows,
        stations,
        quantiles,
        spec,
        config["candidates"][family]["random_state"],
    )
    xtest = feature_matrix(test_rows, stations)
    predicted = np.column_stack([fitted.predict(xtest) for fitted in models])
    predicted.sort(axis=1)
    low = predicted[:, 0] + (predicted[:, 1] - predicted[:, 0]) * (
        (0.001 - quantiles[0]) / (quantiles[1] - quantiles[0])
    )
    high = predicted[:, -1] + (predicted[:, -1] - predicted[:, -2]) * (
        (0.999 - quantiles[-1]) / (quantiles[-1] - quantiles[-2])
    )
    anchors_p = np.array([0.001, *quantiles, 0.999])
    anchors = np.column_stack([low, predicted, high])
    anchors.sort(axis=1)
    return np.vstack(
        [np.interp(probabilities, anchors_p, row) for row in anchors]
    )


def score_samples(
    rows: list[dict], residual_draws: np.ndarray, probability_floor: float
) -> tuple[dict, list[dict]]:
    points = np.array([row["point_f"] for row in rows])
    actual = np.array([row["actual_f"] for row in rows])
    samples = np.sort(points[:, None] + residual_draws, axis=1)
    sample_count = samples.shape[1]
    coefficients = 2 * np.arange(1, sample_count + 1) - sample_count - 1
    crps = np.mean(np.abs(samples - actual[:, None]), axis=1) - np.sum(
        samples * coefficients[None, :], axis=1
    ) / sample_count**2
    edges = np.arange(20.0, 122.0, 2.0)
    cdf = np.column_stack(
        [np.mean(samples < edge, axis=1) for edge in edges]
    )
    probabilities = np.diff(
        np.column_stack([np.zeros(len(rows)), cdf, np.ones(len(rows))]), axis=1
    )
    probabilities = np.maximum(probabilities, probability_floor)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    outcome_bins = np.searchsorted(edges, actual, side="right")
    selected_probability = probabilities[np.arange(len(rows)), outcome_bins]
    log_loss = -np.log(selected_probability)
    targets = np.zeros_like(probabilities)
    targets[np.arange(len(rows)), outcome_bins] = 1
    brier = np.sum((probabilities - targets) ** 2, axis=1)
    lower80 = np.quantile(samples, 0.1, axis=1)
    upper80 = np.quantile(samples, 0.9, axis=1)
    lower90 = np.quantile(samples, 0.05, axis=1)
    upper90 = np.quantile(samples, 0.95, axis=1)
    covered80 = (actual >= lower80) & (actual <= upper80)
    covered90 = (actual >= lower90) & (actual <= upper90)
    per_row = [
        {
            "station": row["station"],
            "target_date": row["target_date"],
            "crps_f": float(crps[index]),
            "log_loss": float(log_loss[index]),
            "brier": float(brier[index]),
            "covered80": bool(covered80[index]),
            "covered90": bool(covered90[index]),
            "width80_f": float(upper80[index] - lower80[index]),
            "width90_f": float(upper90[index] - lower90[index]),
        }
        for index, row in enumerate(rows)
    ]
    aggregate = {
        "events": len(rows),
        "mean_crps_f": float(np.mean(crps)),
        "categorical_log_loss": float(np.mean(log_loss)),
        "mean_multiclass_brier": float(np.mean(brier)),
        "coverage80": float(np.mean(covered80)),
        "coverage90": float(np.mean(covered90)),
        "mean_width80_f": float(np.mean(upper80 - lower80)),
        "mean_width90_f": float(np.mean(upper90 - lower90)),
    }
    return aggregate, per_row


def candidate_variants(config: dict) -> list[dict]:
    variants = [{"family": "gaussian_residual", "spec": {}}]
    variants.extend(
        {
            "family": "student_t_residual",
            "spec": {"degrees_of_freedom": degrees},
        }
        for degrees in config["candidates"]["student_t_residual"]["degrees_of_freedom"]
    )
    variants.extend(
        {
            "family": "empirical_residual",
            "spec": {"gaussian_jitter_bandwidth_f": bandwidth},
        }
        for bandwidth in config["candidates"]["empirical_residual"][
            "gaussian_jitter_bandwidth_f"
        ]
    )
    variants.extend(
        {"family": "quantile_gbt_residual", "spec": spec}
        for spec in config["candidates"]["quantile_gbt_residual"]["parameter_grid"]
    )
    return variants


def evaluate_variant(variant: dict, rows: list[dict], config: dict) -> dict:
    stations = sorted({row["station"] for row in rows})
    fold_metrics = {}
    scored_rows = []
    for fold_index, heldout in enumerate(stations):
        train = [row for row in rows if row["station"] != heldout]
        test = [row for row in rows if row["station"] == heldout]
        samples = residual_samples(
            variant["family"],
            variant["spec"],
            train,
            test,
            stations,
            config,
            config["distribution_numerics"]["empirical_jitter_seed"] + fold_index,
        )
        aggregate, details = score_samples(
            test,
            samples,
            config["distribution_numerics"]["categorical_probability_floor"],
        )
        fold_metrics[heldout] = aggregate
        scored_rows.extend(details)
    pooled = {
        "events": len(scored_rows),
        "mean_crps_f": float(np.mean([row["crps_f"] for row in scored_rows])),
        "categorical_log_loss": float(
            np.mean([row["log_loss"] for row in scored_rows])
        ),
        "mean_multiclass_brier": float(np.mean([row["brier"] for row in scored_rows])),
        "coverage80": float(np.mean([row["covered80"] for row in scored_rows])),
        "coverage90": float(np.mean([row["covered90"] for row in scored_rows])),
        "mean_width80_f": float(np.mean([row["width80_f"] for row in scored_rows])),
        "mean_width90_f": float(np.mean([row["width90_f"] for row in scored_rows])),
    }
    return {**variant, "fold_metrics": fold_metrics, "pooled": pooled}


def fit_final_artifact(
    selected: dict, rows: list[dict], config: dict, output: Path
) -> dict:
    stations = sorted({row["station"] for row in rows})
    if selected["family"] == "quantile_gbt_residual":
        quantiles = config["candidates"]["quantile_gbt_residual"]["quantiles"]
        fitted = fit_quantile_gbt(
            rows,
            stations,
            quantiles,
            selected["spec"],
            config["candidates"]["quantile_gbt_residual"]["random_state"],
        )
        artifact_path = output / "quantile_gbt.joblib"
        joblib.dump({"models": fitted, "stations": stations, "quantiles": quantiles}, artifact_path)
        return {"path": str(artifact_path), "sha256": sha256_path(artifact_path)}
    draws = residual_samples(
        selected["family"], selected["spec"], rows, rows[:1], stations, config, 20260912
    )[0]
    artifact = {
        "family": selected["family"],
        "spec": selected["spec"],
        "development_stations": stations,
        "residual_sample_f": draws.tolist(),
    }
    artifact_path = output / "probability_model.json"
    artifact_path.write_text(json.dumps(artifact, sort_keys=True) + "\n")
    return {"path": str(artifact_path), "sha256": sha256_path(artifact_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    parent = Path(config["parent_design"])
    if sha256_path(parent) != config["parent_design_sha256"]:
        raise ValueError("parent probability design checksum mismatch")
    rows = load_development_rows(config)
    expected_stations = {"KORD", "KJFK", "KLAX", "KDFW", "KMIA", "KSEA"}
    if {row["station"] for row in rows} != expected_stations:
        raise ValueError("development station set mismatch")
    evaluations = [
        evaluate_variant(variant, rows, config)
        for variant in candidate_variants(config)
    ]
    family_order = {
        "gaussian_residual": 0,
        "student_t_residual": 1,
        "empirical_residual": 2,
        "quantile_gbt_residual": 3,
    }
    evaluations.sort(
        key=lambda row: (
            row["pooled"]["mean_crps_f"],
            row["pooled"]["categorical_log_loss"],
            abs(row["pooled"]["coverage80"] - 0.8),
            family_order[row["family"]],
        )
    )
    selected = evaluations[0]
    args.output.mkdir(parents=True)
    artifact = fit_final_artifact(selected, rows, config, args.output)
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "development_row_count": len(rows),
        "development_station_counts": {
            station: sum(row["station"] == station for row in rows)
            for station in sorted(expected_stations)
        },
        "ranking": evaluations,
        "selected": {
            "family": selected["family"],
            "spec": selected["spec"],
            "pooled_loso_metrics": selected["pooled"],
        },
        "frozen_model_artifact": artifact,
        "decision": "DEVELOPMENT_CANDIDATE_FROZEN",
        "boundary": config["boundary"],
    }
    result_path = args.output / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "development_row_count": result["development_row_count"],
                "ranking": [
                    {"family": row["family"], "spec": row["spec"], "pooled": row["pooled"]}
                    for row in evaluations
                ],
                "selected": result["selected"],
                "frozen_model_artifact": artifact,
                "decision": result["decision"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
