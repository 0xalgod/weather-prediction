#!/usr/bin/env python3
"""Score locked Chicago probability baselines and point-in-time market coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from weather_quant.backtest.scoring import (
    mean_metrics,
    ordered_rows,
    paired_bootstrap_mean_difference,
    score_probabilities,
)
from weather_quant.market_model.vertical_slice import (
    gaussian_bucket_probabilities,
    quantile_bucket_probabilities,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def market_histories(run_directory: Path) -> dict[str, list[dict[str, Any]]]:
    coverage = [
        json.loads(line)
        for line in (run_directory / "coverage.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    histories = {}
    for index, row in enumerate(coverage):
        envelope = json.loads(
            (run_directory / "responses" / f"token-{index:04d}.json").read_text(encoding="utf-8")
        )
        payload = json.loads(envelope["body_text"])
        histories[str(row["yes_token_id"])] = payload["history"]
    return histories


def market_vector(
    buckets: list[dict[str, Any]],
    histories: dict[str, list[dict[str, Any]]],
    decision_timestamp: int,
    maximum_staleness: int,
) -> tuple[list[float] | None, dict[str, Any]]:
    prices = []
    staleness = []
    for bucket in buckets:
        eligible = [
            point
            for point in histories[str(bucket["yes_token_id"])]
            if int(point["t"]) <= decision_timestamp
        ]
        if not eligible:
            return None, {"reason": "NO_POINT_AT_OR_BEFORE_DECISION"}
        point = max(eligible, key=lambda item: int(item["t"]))
        age = decision_timestamp - int(point["t"])
        if age > maximum_staleness:
            return None, {"reason": "POINT_TOO_STALE", "maximum_observed_staleness": age}
        price = float(point["p"])
        if price <= 0:
            return None, {"reason": "NON_POSITIVE_PRICE"}
        prices.append(price)
        staleness.append(age)
    raw_sum = sum(prices)
    return [price / raw_sum for price in prices], {
        "reason": None,
        "raw_yes_price_sum": raw_sum,
        "maximum_staleness_seconds": max(staleness),
    }


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"immutable output exists: {args.output}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    join_path = Path(config["join_source"])
    if sha256_path(join_path) != config["join_source_sha256"]:
        raise ValueError("join source checksum mismatch")
    joined = json.loads(join_path.read_text(encoding="utf-8"))["rows"]
    joined.sort(key=lambda row: row["target_local_date"])
    price_run = Path(config["price_history_source"])
    histories = market_histories(price_run)
    validation_count = int(config["split"]["validation_event_count"])
    probability_floor = float(config["metrics"]["probability_floor_for_log_loss"])
    maximum_staleness = int(config["indicative_market"]["maximum_staleness_seconds"])
    event_results = []
    market_reason_counts: dict[str, int] = defaultdict(int)
    for event_index, row in enumerate(joined):
        buckets = ordered_rows(row["buckets"])
        forecast = row["forecast"]
        winner_index = next(
            index
            for index, bucket in enumerate(buckets)
            if bucket["market_id"] == row["winning_market_id"]
        )
        models = {
            "uniform": [1 / len(buckets)] * len(buckets),
            "nbm_gaussian": [
                item["model_probability"]
                for item in gaussian_bucket_probabilities(
                    buckets, forecast["mean_f"], forecast["standard_deviation_f"]
                )
            ],
            "nbm_quantile_preserving": [
                item["model_probability"]
                for item in quantile_bucket_probabilities(buckets, forecast)
            ],
        }
        decision_timestamp = int(
            datetime.fromisoformat(row["decision_time_utc"].replace("Z", "+00:00")).timestamp()
        )
        indicative, market_quality = market_vector(
            buckets, histories, decision_timestamp, maximum_staleness
        )
        if indicative is not None:
            models["indicative_market"] = indicative
        else:
            market_reason_counts[market_quality["reason"]] += 1
        event_results.append(
            {
                "event_id": row["event_id"],
                "target_local_date": row["target_local_date"],
                "split": "validation" if event_index < validation_count else "test",
                "winner_index": winner_index,
                "winning_bucket_label": row["winning_bucket_label"],
                "market_quality": market_quality,
                "models": {
                    name: {
                        "probabilities": probabilities,
                        "metrics": score_probabilities(
                            probabilities, winner_index, probability_floor
                        ),
                    }
                    for name, probabilities in models.items()
                },
            }
        )

    aggregate = {}
    for split in ("validation", "test"):
        split_rows = [row for row in event_results if row["split"] == split]
        aggregate[split] = {}
        for model in config["models"]:
            aggregate[split][model] = mean_metrics(
                [row["models"][model]["metrics"] for row in split_rows]
            )
        market_rows = [row for row in split_rows if "indicative_market" in row["models"]]
        aggregate[split]["indicative_market_event_count"] = len(market_rows)
        if market_rows:
            aggregate[split]["indicative_market"] = mean_metrics(
                [row["models"]["indicative_market"]["metrics"] for row in market_rows]
            )

    bootstrap = {}
    for split in ("validation", "test"):
        split_rows = [row for row in event_results if row["split"] == split]
        bootstrap[split] = paired_bootstrap_mean_difference(
            [row["models"]["nbm_gaussian"]["metrics"]["multiclass_log_loss"] for row in split_rows],
            [
                row["models"]["nbm_quantile_preserving"]["metrics"]["multiclass_log_loss"]
                for row in split_rows
            ],
            int(config["metrics"]["paired_bootstrap_repetitions"]),
            int(config["metrics"]["paired_bootstrap_seed"]),
        )
    test_market_count = aggregate["test"]["indicative_market_event_count"]
    market_status = (
        "AVAILABLE"
        if test_market_count
        >= config["acceptance_thresholds"]["market_comparison_minimum_event_count"]
        else "INSUFFICIENT_POINT_IN_TIME_COVERAGE"
    )
    preliminary = {}
    for model in ("nbm_gaussian", "nbm_quantile_preserving"):
        preliminary[model] = (
            "PRELIMINARY_BETTER_BASELINE"
            if all(
                aggregate[split][model]["multiclass_log_loss"]
                < aggregate[split]["uniform"]["multiclass_log_loss"]
                for split in ("validation", "test")
            )
            else "DOES_NOT_BEAT_UNIFORM_BOTH_SPLITS"
        )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now().astimezone().isoformat(),
        "config": config,
        "event_count": len(event_results),
        "aggregate_metrics": aggregate,
        "gaussian_minus_quantile_log_loss_bootstrap": bootstrap,
        "indicative_market_status": market_status,
        "indicative_market_reason_counts": dict(market_reason_counts),
        "preliminary_model_decisions": preliminary,
        "events": event_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in result if key != "events"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
