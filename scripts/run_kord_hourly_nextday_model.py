#!/usr/bin/env python3
"""Build leakage-safe hourly features and run the preregistered next-day max model."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.probe_multicity_price_horizons import sha256_path, utc_now


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def finite(values: list[float | None]) -> list[float]:
    return [float(value) for value in values if value is not None and math.isfinite(value)]


def mean(values: list[float | None]) -> float:
    admitted = finite(values)
    return float(np.mean(admitted)) if admitted else math.nan


def build_features(hourly: list[dict], labels: list[dict]) -> tuple[list[str], list[dict]]:
    by_date: dict[str, list[dict]] = defaultdict(list)
    for row in hourly:
        if row["hour_local_standard"] <= 18:
            by_date[row["date_local_standard"]].append(row)
    target = {row["date"]: row["daily_maximum_dry_bulb_c"] for row in labels}
    names = ["sin_doy", "cos_doy"] + [f"temp_h{hour:02d}" for hour in range(19)]
    names += [
        "temp_min",
        "temp_max",
        "temp_mean",
        "temp_std",
        "temp_latest",
        "temp_slope_12_18",
        "dew_mean",
        "dew_latest",
        "rh_mean",
        "rh_latest",
        "wind_mean",
        "wind_max",
        "gust_max",
        "pressure_mean",
        "pressure_latest",
        "pressure_change",
        "visibility_mean",
        "precip_sum",
        "hour_count",
        "observation_count",
        "label_lag2",
        "label_lag3",
        "label_lag7",
        "label_roll3",
        "label_roll7",
        "label_roll14",
        "label_roll14_std",
    ]
    output = []
    for target_date in sorted(target):
        current = date.fromisoformat(target_date)
        input_date = (current - timedelta(days=1)).isoformat()
        observations = sorted(by_date[input_date], key=lambda row: row["timestamp_local_standard"])
        hourly_temps = {
            hour: mean([r["dry_bulb_c"] for r in observations if r["hour_local_standard"] == hour])
            for hour in range(19)
        }
        temps = finite([r["dry_bulb_c"] for r in observations])
        recent = [(h, hourly_temps[h]) for h in range(12, 19) if math.isfinite(hourly_temps[h])]
        slope = (
            float(np.polyfit([x[0] for x in recent], [x[1] for x in recent], 1)[0])
            if len(recent) >= 2
            else math.nan
        )
        latest = observations[-1] if observations else {}
        pressures = finite([r["sea_level_pressure_hpa"] for r in observations])
        lags = {lag: target.get((current - timedelta(days=lag)).isoformat()) for lag in (2, 3, 7)}
        rolling = {}
        for window in (3, 7, 14):
            vals = finite(
                [
                    target.get((current - timedelta(days=lag)).isoformat())
                    for lag in range(2, window + 2)
                ]
            )
            rolling[window] = float(np.mean(vals)) if vals else math.nan
            if window == 14:
                rolling["14_std"] = float(np.std(vals)) if vals else math.nan
        doy = current.timetuple().tm_yday
        values = [math.sin(2 * math.pi * doy / 365.25), math.cos(2 * math.pi * doy / 365.25)] + [
            hourly_temps[h] for h in range(19)
        ]
        values += [
            min(temps) if temps else math.nan,
            max(temps) if temps else math.nan,
            float(np.mean(temps)) if temps else math.nan,
            float(np.std(temps)) if temps else math.nan,
            latest.get("dry_bulb_c", math.nan),
            slope,
            mean([r["dew_point_c"] for r in observations]),
            latest.get("dew_point_c", math.nan),
            mean([r["relative_humidity_pct"] for r in observations]),
            latest.get("relative_humidity_pct", math.nan),
            mean([r["wind_speed_ms"] for r in observations]),
            max(finite([r["wind_speed_ms"] for r in observations]), default=math.nan),
            max(finite([r["wind_gust_ms"] for r in observations]), default=math.nan),
            float(np.mean(pressures)) if pressures else math.nan,
            latest.get("sea_level_pressure_hpa", math.nan),
            pressures[-1] - pressures[0] if len(pressures) >= 2 else math.nan,
            mean([r["visibility_km"] for r in observations]),
            sum(finite([r["precipitation_mm"] for r in observations])),
            len({r["hour_local_standard"] for r in observations if r["dry_bulb_c"] is not None}),
            len(observations),
            lags[2],
            lags[3],
            lags[7],
            rolling[3],
            rolling[7],
            rolling[14],
            rolling["14_std"],
        ]
        output.append(
            {
                "target_date": target_date,
                "features": dict(zip(names, values)),
                "target_c": target[target_date],
            }
        )
    return names, output


def metrics(y: np.ndarray, prediction: np.ndarray) -> dict:
    error = prediction - y
    return {
        "mae_c": float(mean_absolute_error(y, prediction)),
        "rmse_c": float(mean_squared_error(y, prediction) ** 0.5),
        "bias_c": float(np.mean(error)),
        "within_1c_rate": float(np.mean(np.abs(error) <= 1)),
        "within_2c_rate": float(np.mean(np.abs(error) <= 2)),
    }


def model(spec: dict) -> Pipeline:
    if spec["family"] == "ridge":
        estimator = Pipeline(
            [
                ("scale", StandardScaler()),
                ("regressor", Ridge(alpha=spec["alpha"], solver="lsqr")),
            ]
        )
    else:
        estimator = HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=300,
            min_samples_leaf=20,
            max_leaf_nodes=spec["leaves"],
            l2_regularization=spec["l2"],
            random_state=20260909,
        )
    return Pipeline(
        [("impute", SimpleImputer(strategy="median", add_indicator=True)), ("model", estimator)]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    hp = Path(config["source_hourly"])
    lp = Path(config["source_labels"])
    if (
        sha256_path(hp) != config["source_hourly_sha256"]
        or sha256_path(lp) != config["source_labels_sha256"]
    ):
        raise ValueError("source checksum mismatch")
    names, rows = build_features(read_jsonl(hp), read_jsonl(lp))
    split = config["temporal_split"]
    minimum_hours = config.get("eligibility", {}).get(
        "minimum_distinct_temperature_hours_through_18_lst", 0
    )
    eligible_rows = [r for r in rows if r["features"]["hour_count"] >= minimum_hours]
    groups = {
        name: [r for r in eligible_rows if bounds[0] <= r["target_date"] <= bounds[1]]
        for name, bounds in ((n, split[n]) for n in ("train", "validation", "test"))
    }
    if any(len(groups[n]) != split["expected_counts"][n] for n in groups):
        raise ValueError("split mismatch")

    def xy(values):
        return np.array([[r["features"][n] for n in names] for r in values]), np.array(
            [r["target_c"] for r in values]
        )

    xtrain, ytrain = xy(groups["train"])
    specs = [
        {"family": "ridge", "alpha": x} for x in config["models"]["candidates"]["ridge_alpha"]
    ] + [
        {"family": "hgb", "leaves": leaves, "l2": regularization}
        for leaves in (7, 15)
        for regularization in (1.0, 10.0)
    ]
    cv = []
    for spec in specs:
        fold = []
        for train_idx, val_idx in TimeSeriesSplit(5).split(xtrain):
            fitted = model(spec).fit(xtrain[train_idx], ytrain[train_idx])
            fold.append(mean_absolute_error(ytrain[val_idx], fitted.predict(xtrain[val_idx])))
        cv.append({"spec": spec, "fold_mae_c": fold, "mean_mae_c": float(np.mean(fold))})
    selected = min(cv, key=lambda r: r["mean_mae_c"])
    champion = model(selected["spec"]).fit(xtrain, ytrain)
    harmonic = LinearRegression().fit(xtrain[:, :2], ytrain)

    def evaluate(name):
        x, y = xy(groups[name])
        persistence = np.array([r["features"]["temp_max"] for r in groups[name]], dtype=float)
        climate = harmonic.predict(x[:, :2])
        persistence = np.where(np.isfinite(persistence), persistence, climate)
        pred = champion.predict(x)
        m = {
            "persistence": metrics(y, persistence),
            "harmonic_climatology": metrics(y, climate),
            "champion": metrics(y, pred),
        }
        return m, pred

    validation, val_pred = evaluate("validation")
    vm = validation
    gates = config["validation_gates"]
    checks = {
        "minimum_mae_improvement_vs_persistence": (
            vm["persistence"]["mae_c"] - vm["champion"]["mae_c"]
        )
        / vm["persistence"]["mae_c"]
        >= gates["minimum_mae_improvement_vs_persistence"],
        "minimum_mae_improvement_vs_harmonic_climatology": (
            vm["harmonic_climatology"]["mae_c"] - vm["champion"]["mae_c"]
        )
        / vm["harmonic_climatology"]["mae_c"]
        >= gates["minimum_mae_improvement_vs_harmonic_climatology"],
        "maximum_absolute_bias_c": abs(vm["champion"]["bias_c"])
        <= gates["maximum_absolute_bias_c"],
    }
    passed = all(checks.values())
    test, test_pred = evaluate("test") if passed else (None, None)
    args.output.mkdir(parents=True)
    feature_path = args.output / "features.jsonl"
    feature_path.write_text(
        "".join(json.dumps(r, sort_keys=True, allow_nan=True) + "\n" for r in rows)
    )
    result = {
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "feature_names": names,
        "feature_count": len(names),
        "ineligible_no_predict_count": len(rows) - len(eligible_rows),
        "split_counts": {k: len(v) for k, v in groups.items()},
        "train_cv": cv,
        "selected": selected,
        "validation": {"metrics": validation, "checks": checks},
        "test": {"consumed": passed, "metrics": test},
        "decision": "TEST_EVALUATED" if passed else "VALIDATION_REJECT_TEST_UNTOUCHED",
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
