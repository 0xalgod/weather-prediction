#!/usr/bin/env python3
"""Build the frozen two-cycle US NBM model-ready dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.build_us_nbm_model_ready_pilot import normalized_prices
from scripts.evaluate_us_nbm_local_day_semantics import station_from_resolution_url
from scripts.probe_multicity_price_horizons import sha256_path, utc_now


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    event_path = Path(config["source_events"])
    price_path = Path(config["source_prices"])
    nbm_path = Path(config["source_nbm"])
    events = {str(row["event_id"]): row for row in json.loads(event_path.read_text())}
    prices = {str(row["event_id"]): row for row in lines(price_path) if row["usable_full_vector"]}
    nbm = {
        (row["target_date"], row["station_code"], row["cycle_utc"]): row for row in lines(nbm_path)
    }
    rows, errors = [], []
    for event_id, price in sorted(
        prices.items(), key=lambda item: (item[1]["target_date"], item[0])
    ):
        try:
            event = events[event_id]
            station = station_from_resolution_url(event["resolution_source"])
            features = {}
            for label, spec in config["cycles"].items():
                source = nbm[(event["target_date"], station, spec["cycle_utc"])]
                if not source["passed"] or source["feature"] is None:
                    raise ValueError(f"missing {label} feature")
                features[label] = source["feature"]
            winners = [
                i for i, bucket in enumerate(event["buckets"]) if bucket["terminal_yes_winner"]
            ]
            if len(winners) != 1:
                raise ValueError("expected one terminal winner")
            probabilities, raw_sum = normalized_prices(event, price)
            rows.append(
                {
                    "event_id": event_id,
                    "city": event["city"],
                    "station_code": station,
                    "target_date": event["target_date"],
                    "temperature_unit": event["temperature_unit"],
                    "buckets": event["buckets"],
                    "winner_bucket_index": winners[0],
                    "price_cutoff_utc": price["cutoff_utc"],
                    "raw_probability_sum": raw_sum,
                    "market_probabilities": probabilities,
                    "nbm_features": features,
                }
            )
        except (KeyError, ValueError) as exc:
            errors.append({"event_id": event_id, "error": f"{type(exc).__name__}: {exc}"})
    counts = Counter(row["city"] for row in rows)
    summary = {
        "join_count": len(rows),
        "date_count": len({row["target_date"] for row in rows}),
        "city_count": len(counts),
        "minimum_events_per_city": min(counts.values(), default=0),
        "maximum_events_per_city": max(counts.values(), default=0),
        "join_error_count": len(errors),
        "duplicate_event_count": len(rows) - len({row["event_id"] for row in rows}),
        "maximum_probability_normalization_error": max(
            (abs(sum(row["market_probabilities"]) - 1) for row in rows), default=0
        ),
        "missing_outcome_count": sum(row["winner_bucket_index"] is None for row in rows),
        "missing_cycle_feature_count": sum(
            any(label not in row["nbm_features"] for label in config["cycles"]) for row in rows
        ),
    }
    g = config["acceptance_thresholds"]
    checks = {
        "exact_join_count": summary["join_count"] == g["exact_join_count"],
        "exact_date_count": summary["date_count"] == g["exact_date_count"],
        "exact_city_count": summary["city_count"] == g["exact_city_count"],
        "exact_events_per_city": summary["minimum_events_per_city"]
        == summary["maximum_events_per_city"]
        == g["exact_events_per_city"],
        "maximum_join_error_count": summary["join_error_count"] <= g["maximum_join_error_count"],
        "maximum_duplicate_event_count": summary["duplicate_event_count"]
        <= g["maximum_duplicate_event_count"],
        "maximum_probability_normalization_error": summary[
            "maximum_probability_normalization_error"
        ]
        <= g["maximum_probability_normalization_error"],
        "maximum_missing_outcome_count": summary["missing_outcome_count"]
        <= g["maximum_missing_outcome_count"],
        "maximum_missing_cycle_feature_count": summary["missing_cycle_feature_count"]
        <= g["maximum_missing_cycle_feature_count"],
    }
    args.output.mkdir(parents=True)
    row_path = args.output / "rows.jsonl"
    row_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "source_sha256": {
            "events": sha256_path(event_path),
            "prices": sha256_path(price_path),
            "nbm": sha256_path(nbm_path),
        },
        "rows_sha256": sha256_path(row_path),
        "summary": summary,
        "checks": checks,
        "errors": errors,
        "decision": "TWO_CYCLE_JOIN_PASS" if all(checks.values()) else "TWO_CYCLE_JOIN_FAIL",
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
