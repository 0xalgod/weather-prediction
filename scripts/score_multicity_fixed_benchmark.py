#!/usr/bin/env python3
"""Score preregistered fixed multi-city probabilistic benchmarks once."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.backtest.scoring import (
    mean_metrics,
    paired_cluster_bootstrap_mean_difference,
    score_probabilities,
)
from weather_quant.market_model.vertical_slice import normal_cdf

MODELS = ("uniform", "normalized_market", "raw_gefs_gaussian", "fixed_market_gefs_blend")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gaussian_vector(buckets: list[dict], mean_f: float, spread_f: float) -> list[float]:
    values = []
    for bucket in buckets:
        lower = (
            0.0
            if bucket["lower_threshold_f"] is None
            else normal_cdf(bucket["lower_threshold_f"], mean_f, spread_f)
        )
        upper = (
            1.0
            if bucket["upper_threshold_f"] is None
            else normal_cdf(bucket["upper_threshold_f"], mean_f, spread_f)
        )
        values.append(max(0.0, upper - lower))
    total = math.fsum(values)
    return [value / total for value in values]


def split_name(target_date: str, config: dict) -> str:
    split = config["chronological_split"]
    if target_date <= split["development_end_date"]:
        return "development"
    if split["validation_start_date"] <= target_date <= split["validation_end_date"]:
        return "validation"
    if target_date >= split["test_start_date"]:
        return "test"
    raise ValueError(f"date falls into an unassigned split gap: {target_date}")


def aggregate(events: list[dict]) -> dict:
    return {
        model: mean_metrics([event["models"][model]["metrics"] for event in events])
        for model in MODELS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    source_path = Path(config["source"])
    if sha256(source_path) != config["source_file_sha256"]:
        raise ValueError("source file checksum mismatch")
    source = json.loads(source_path.read_text())
    if source["rows_sha256"] != config["source_rows_sha256"]:
        raise ValueError("source row checksum mismatch")
    floor = config["metrics"]["probability_floor"]
    city_counts = Counter(row["city"] for row in source["rows"])
    events = []
    invalid_vectors = 0
    for row in source["rows"]:
        buckets = row["buckets"]
        market = [bucket["market_probability_normalized"] for bucket in buckets]
        gefs = gaussian_vector(
            buckets,
            row["gefs_overlap_mean_max_f"],
            max(row["gefs_overlap_spread_at_mean_max_f"], 1.0),
        )
        vectors = {
            "uniform": [1 / len(buckets)] * len(buckets),
            "normalized_market": market,
            "raw_gefs_gaussian": gefs,
            "fixed_market_gefs_blend": [
                0.5 * market_value + 0.5 * gefs_value
                for market_value, gefs_value in zip(market, gefs)
            ],
        }
        invalid_vectors += sum(abs(math.fsum(vector) - 1) > 1e-9 for vector in vectors.values())
        tail_winner = row["winner_index"] in {0, len(buckets) - 1}
        events.append(
            {
                "event_id": row["event_id"],
                "target_date": row["target_date"],
                "city": row["city"],
                "split": split_name(row["target_date"], config),
                "slice_values": {
                    "temperature_unit": row["temperature_unit"],
                    "gefs_exact_partition": row["gefs_exact_partition"],
                    "tail_winner": tail_winner,
                    "city_event_count": city_counts[row["city"]],
                },
                "models": {
                    model: {
                        "probabilities": vectors[model],
                        "metrics": score_probabilities(vectors[model], row["winner_index"], floor),
                    }
                    for model in MODELS
                },
            }
        )
    split_events = {
        name: [event for event in events if event["split"] == name]
        for name in ("development", "validation", "test")
    }
    expected = config["chronological_split"]
    split_checks = {
        "development": len(split_events["development"]) == expected["expected_development_events"],
        "validation": len(split_events["validation"]) == expected["expected_validation_events"],
        "test": len(split_events["test"]) == expected["expected_test_events"],
    }
    aggregate_metrics = {name: aggregate(rows) for name, rows in split_events.items()}
    test = split_events["test"]
    paired = paired_cluster_bootstrap_mean_difference(
        [
            event["models"]["fixed_market_gefs_blend"]["metrics"][
                "multiclass_log_loss"
            ]
            for event in test
        ],
        [
            event["models"]["normalized_market"]["metrics"]["multiclass_log_loss"]
            for event in test
        ],
        [event["target_date"] for event in test],
        config["metrics"]["cluster_bootstrap_repetitions"],
        config["metrics"]["cluster_bootstrap_seed"],
    )
    blend_loss = aggregate_metrics["test"]["fixed_market_gefs_blend"]["multiclass_log_loss"]
    market_loss = aggregate_metrics["test"]["normalized_market"]["multiclass_log_loss"]
    relative_improvement = (market_loss - blend_loss) / market_loss
    brier_difference = (
        aggregate_metrics["test"]["fixed_market_gefs_blend"]["multiclass_brier_score"]
        - aggregate_metrics["test"]["normalized_market"]["multiclass_brier_score"]
    )
    gate = config["promotion_gate"]
    checks = {
        "split_counts": all(split_checks.values()),
        "minimum_test_event_count": len(test) >= gate["minimum_test_event_count"],
        "minimum_relative_test_log_loss_improvement_vs_market": relative_improvement
        >= gate["minimum_relative_test_log_loss_improvement_vs_market"],
        "maximum_test_brier_difference_vs_market": brier_difference
        <= gate["maximum_test_brier_difference_vs_market"],
        "maximum_cluster_bootstrap_ci95_upper_log_loss_difference": paired["ci95_upper"]
        < gate["maximum_cluster_bootstrap_ci95_upper_log_loss_difference"],
        "maximum_invalid_probability_vector_count": invalid_vectors
        <= gate["maximum_invalid_probability_vector_count"],
    }
    slice_metrics = {}
    for field in config["slices"]:
        slice_metrics[field] = {}
        for value in sorted({str(event["slice_values"][field]) for event in events}):
            subset = [event for event in events if str(event["slice_values"][field]) == value]
            slice_metrics[field][value] = {"event_count": len(subset), "models": aggregate(subset)}
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "source_sha256": sha256(source_path),
        "quality": {
            "event_count": len(events),
            "split_counts": {name: len(rows) for name, rows in split_events.items()},
            "split_checks": split_checks,
            "invalid_probability_vector_count": invalid_vectors,
        },
        "aggregate_metrics": aggregate_metrics,
        "test_blend_vs_market": {
            "relative_log_loss_improvement": relative_improvement,
            "brier_difference": brier_difference,
            "cluster_bootstrap": paired,
        },
        "checks": checks,
        "decision": (
            "FIXED_BLEND_PROMOTE_RESEARCH"
            if all(checks.values())
            else "FIXED_BLEND_REJECT"
        ),
        "slice_metrics": slice_metrics,
        "events": events,
        "boundary": config["boundary"],
    }
    args.output.parent.mkdir(parents=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    console = {
        key: value
        for key, value in result.items()
        if key not in {"events", "slice_metrics"}
    }
    print(json.dumps(console, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
