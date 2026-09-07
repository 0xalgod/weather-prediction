#!/usr/bin/env python3
"""Join frozen US events, market eligibility, NBM features, and window metadata."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.evaluate_us_nbm_local_day_semantics import (
    evaluate_window,
    station_from_resolution_url,
)
from scripts.probe_multicity_price_horizons import sha256_path


def normalized_prices(event: dict, price_row: dict) -> tuple[list[float], float]:
    prices_by_market = {
        str(point["market_id"]): float(point["price"])
        for point in price_row["points"]
    }
    prices = [prices_by_market[str(bucket["market_id"])] for bucket in event["buckets"]]
    raw_sum = sum(prices)
    if len(prices) != len(event["buckets"]) or raw_sum <= 0:
        raise ValueError("market vector is incomplete or non-positive")
    return [price / raw_sum for price in prices], raw_sum


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--eligibility", type=Path, required=True)
    parser.add_argument("--nbm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")

    config = json.loads(args.config.read_text())
    events_path = args.selection / "selected-events.json"
    events = json.loads(events_path.read_text())
    price_rows_path = args.prices / "event-horizon-coverage.jsonl"
    price_rows = {
        str(row["event_id"]): row
        for row in (json.loads(line) for line in price_rows_path.read_text().splitlines())
    }
    eligibility_path = args.eligibility / "classified-events.jsonl"
    eligibility = {
        str(row["event_id"]): row
        for row in (json.loads(line) for line in eligibility_path.read_text().splitlines())
    }
    nbm_path = args.nbm / "station-dates.jsonl"
    nbm_rows = [json.loads(line) for line in nbm_path.read_text().splitlines()]
    nbm = {(row["target_date"], row["station_code"]): row for row in nbm_rows}
    semantics_config = json.loads(Path(config["source_semantics_config"]).read_text())
    offsets = semantics_config["probe"]["nbm_window_offsets_from_target_00z_utc_hours"]

    rows = []
    errors = []
    for event in events:
        event_id = str(event["event_id"])
        try:
            station = station_from_resolution_url(event["resolution_source"])
            nbm_row = nbm[(event["target_date"], station)]
            if not nbm_row["passed"] or nbm_row["feature"] is None:
                raise ValueError("NBM feature is unavailable")
            price_row = price_rows[event_id]
            eligibility_row = eligibility[event_id]
            status = eligibility_row["eligibility"]
            market_probabilities = None
            raw_probability_sum = None
            if status == "PRICE_ELIGIBLE":
                market_probabilities, raw_probability_sum = normalized_prices(event, price_row)
            winners = [
                index
                for index, bucket in enumerate(event["buckets"])
                if bucket["terminal_yes_winner"]
            ]
            if len(winners) != 1:
                raise ValueError("expected exactly one terminal winner")
            timezone_name = semantics_config["cities"][event["city"]]["timezone"]
            window = evaluate_window(event["target_date"], timezone_name, offsets)
            rows.append(
                {
                    "event_id": event_id,
                    "city": event["city"],
                    "station_code": station,
                    "target_date": event["target_date"],
                    "end_date_utc": event["end_date_utc"],
                    "temperature_unit": event["temperature_unit"],
                    "buckets": event["buckets"],
                    "winner_bucket_index": winners[0],
                    "price_eligibility": status,
                    "price_cutoff_utc": price_row["cutoff_utc"],
                    "raw_probability_sum": raw_probability_sum,
                    "market_probabilities": market_probabilities,
                    "nbm_feature_label": config["join_contract"]["forecast_label"],
                    "nbm_feature": nbm_row["feature"],
                    "proxy_window": window,
                }
            )
        except (KeyError, ValueError) as exc:
            errors.append({"event_id": event_id, "error": f"{type(exc).__name__}: {exc}"})

    eligible = [row for row in rows if row["price_eligibility"] == "PRICE_ELIGIBLE"]
    normalization_errors = [
        abs(sum(row["market_probabilities"]) - 1.0)
        for row in eligible
        if row["market_probabilities"] is not None
    ]
    no_trade = [row for row in rows if row["price_eligibility"] != "PRICE_ELIGIBLE"]
    duplicate_count = len(rows) - len({row["event_id"] for row in rows})
    summary = {
        "source_event_count": len(events),
        "retained_event_count": len(rows),
        "join_error_count": len(errors),
        "price_eligible_join_count": len(eligible),
        "no_trade_retained_count": len(no_trade),
        "city_count": len({row["city"] for row in rows}),
        "target_date_count": len({row["target_date"] for row in rows}),
        "duplicate_event_count": duplicate_count,
        "maximum_probability_normalization_error": max(normalization_errors, default=0.0),
        "nbm_missing_count": sum(row["nbm_feature"] is None for row in rows),
        "no_trade_with_normalized_vector_count": sum(
            row["market_probabilities"] is not None for row in no_trade
        ),
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "retain_all_frozen_events": summary["retained_event_count"]
        == summary["source_event_count"]
        == 220,
        "minimum_final_join_count": len(eligible) >= gates["minimum_final_join_count"],
        "exact_city_count": summary["city_count"] == gates["exact_city_count"],
        "zero_join_errors": len(errors) == 0,
        "zero_duplicate_events": duplicate_count == 0,
        "zero_nbm_missing": summary["nbm_missing_count"] == 0,
        "zero_no_trade_normalized_vectors": summary["no_trade_with_normalized_vector_count"] == 0,
        "normalized_vectors_sum_to_one": summary["maximum_probability_normalization_error"] <= 1e-9,
    }
    args.output.mkdir(parents=True)
    (args.output / "rows.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "stage": "model_ready_join",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256_path(args.config),
        "selected_events_sha256": sha256_path(events_path),
        "price_rows_sha256": sha256_path(price_rows_path),
        "eligibility_rows_sha256": sha256_path(eligibility_path),
        "nbm_rows_sha256": sha256_path(nbm_path),
        "summary": summary,
        "checks": checks,
        "errors": errors,
        "decision": "MODEL_READY_JOIN_PASS" if all(checks.values()) else "MODEL_READY_JOIN_FAIL",
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
