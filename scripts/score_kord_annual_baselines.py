#!/usr/bin/env python3
"""Score pre-registered raw KORD forecast baselines in expanding walk-forward order."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

from weather_quant.backtest.scoring import (
    mean_metrics,
    paired_bootstrap_mean_difference,
    score_probabilities,
)
from weather_quant.market_model.vertical_slice import (
    normal_cdf,
    quantile_cdf_anchors,
    quantile_preserving_cdf,
)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integer_celsius_buckets(minimum: int, maximum: int) -> list[dict]:
    buckets = []
    for value in range(minimum, maximum + 1):
        lower_c = None if value == minimum else value - 0.5
        upper_c = None if value == maximum else value + 0.5
        buckets.append(
            {
                "value_c": value,
                "lower_bound": None if lower_c is None else lower_c * 9 / 5 + 32,
                "upper_bound": None if upper_c is None else upper_c * 9 / 5 + 32,
            }
        )
    return buckets


def gaussian_vector(buckets: list[dict], mean_f: float, spread_f: float) -> list[float]:
    probabilities = []
    for row in buckets:
        lower = 0.0 if row["lower_bound"] is None else normal_cdf(
            row["lower_bound"], mean_f, spread_f
        )
        upper = 1.0 if row["upper_bound"] is None else normal_cdf(
            row["upper_bound"], mean_f, spread_f
        )
        probabilities.append(upper - lower)
    return probabilities


def quantile_vector(buckets: list[dict], row: dict) -> list[float]:
    forecast = {key: row[f"nbm_{key}"] for key in ("p10_f", "p25_f", "p50_f", "p75_f", "p90_f")}
    anchors = quantile_cdf_anchors(**forecast)
    probabilities = []
    for bucket in buckets:
        lower = 0.0 if bucket["lower_bound"] is None else quantile_preserving_cdf(
            bucket["lower_bound"], anchors
        )
        upper = 1.0 if bucket["upper_bound"] is None else quantile_preserving_cdf(
            bucket["upper_bound"], anchors
        )
        probabilities.append(upper - lower)
    return probabilities


def circular_day_distance(left: int, right: int) -> int:
    distance = abs(left - right)
    return min(distance, 365 - distance)


def climatology_parameters(
    train: list[dict], target: dict, config: dict
) -> tuple[float, float, int]:
    target_day = date.fromisoformat(target["target_date"]).timetuple().tm_yday
    half_window = config["day_of_year_half_window"]
    local = [
        row["daily_maximum_dry_bulb_f"]
        for row in train
        if circular_day_distance(
            date.fromisoformat(row["target_date"]).timetuple().tm_yday, target_day
        )
        <= half_window
    ]
    values = local if len(local) >= config["minimum_local_sample"] else [
        row["daily_maximum_dry_bulb_f"] for row in train
    ]
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
    spread = max(math.sqrt(variance), config["standard_deviation_floor_f"])
    return mean, spread, len(values)


def slice_metrics(events: list[dict], field: str) -> dict:
    values = sorted({str(row["slice_values"][field]) for row in events})
    result = {}
    for value in values:
        selected = [row for row in events if str(row["slice_values"][field]) == value]
        result[value] = {
            "event_count": len(selected),
            "models": {
                model: mean_metrics([row["models"][model]["metrics"] for row in selected])
                for model in selected[0]["models"]
            },
        }
    return result


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
        raise ValueError("source row checksum mismatch")

    development_end = config["eligibility"]["development_end_date"]
    development = sorted(
        (row for row in source["rows"] if row["target_date"] <= development_end),
        key=lambda row: row["target_date"],
    )
    initial = config["walk_forward"]["initial_train_events"]
    bins = config["outcome_bins_c"]
    buckets = integer_celsius_buckets(bins["minimum_integer"], bins["maximum_integer"])
    floor = config["metrics"]["probability_floor"]
    model_names = tuple(config["models"])
    events = []
    for index in range(initial, len(development)):
        train = development[:index]
        row = development[index]
        climatology = config["models"]["seasonal_climatology_gaussian"]
        climate_mean, climate_spread, climate_count = climatology_parameters(
            train, row, climatology
        )
        vectors = {
            "seasonal_climatology_gaussian": gaussian_vector(
                buckets, climate_mean, climate_spread
            ),
            "raw_nbm_gaussian": gaussian_vector(
                buckets,
                row["nbm_mean_f"],
                max(
                    row["nbm_standard_deviation_f"],
                    config["models"]["raw_nbm_gaussian"]["standard_deviation_floor_f"],
                ),
            ),
            "raw_nbm_quantile": quantile_vector(buckets, row),
            "raw_gefs_gaussian": gaussian_vector(
                buckets,
                row["gefs_overlap_mean_max_f"],
                max(
                    row["gefs_overlap_spread_at_mean_max_f"],
                    config["models"]["raw_gefs_gaussian"]["standard_deviation_floor_f"],
                ),
            ),
        }
        label_c = round((row["daily_maximum_dry_bulb_f"] - 32) * 5 / 9)
        winner = label_c - bins["minimum_integer"]
        events.append(
            {
                "target_date": row["target_date"],
                "train_event_count": len(train),
                "label_integer_c": label_c,
                "climatology_sample_count": climate_count,
                "slice_values": {
                    "nbm_version": row["nbm_version"],
                    "gefs_exact_partition": row["gefs_exact_partition"],
                    "month": date.fromisoformat(row["target_date"]).month,
                },
                "models": {
                    name: {
                        "metrics": score_probabilities(vectors[name], winner, floor),
                        "probability_sum": math.fsum(vectors[name]),
                    }
                    for name in model_names
                },
            }
        )

    aggregate = {
        name: mean_metrics([row["models"][name]["metrics"] for row in events])
        for name in model_names
    }
    bootstrap = {
        name: paired_bootstrap_mean_difference(
            [row["models"][name]["metrics"]["multiclass_log_loss"] for row in events],
            [
                row["models"]["seasonal_climatology_gaussian"]["metrics"][
                    "multiclass_log_loss"
                ]
                for row in events
            ],
            config["metrics"]["paired_date_bootstrap_repetitions"],
            config["metrics"]["paired_date_bootstrap_seed"],
        )
        for name in model_names
        if name != "seasonal_climatology_gaussian"
    }
    invalid_vectors = sum(
        abs(model["probability_sum"] - 1) > config["decision_rules"]["probability_sum_tolerance"]
        for row in events
        for model in row["models"].values()
    )
    quality = {
        "development_event_count": len(development),
        "initial_train_event_count": initial,
        "oos_event_count": len(events),
        "first_oos_date": events[0]["target_date"],
        "last_oos_date": events[-1]["target_date"],
        "invalid_probability_vector_count": invalid_vectors,
    }
    quality["passed"] = (
        len(events) >= config["decision_rules"]["minimum_oos_events"]
        and invalid_vectors == 0
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "quality": quality,
        "aggregate_metrics": aggregate,
        "log_loss_minus_climatology_bootstrap": bootstrap,
        "slice_metrics": {field: slice_metrics(events, field) for field in config["slices"]},
        "interpretation": "DESCRIPTIVE_DEVELOPMENT_OOS_NOT_FINAL_TEST",
        "trading_authorized": False,
        "events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console_result = {
        key: value for key, value in result.items() if key not in {"events", "slice_metrics"}
    }
    print(json.dumps(console_result, indent=2))
    if not quality["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
