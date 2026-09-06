#!/usr/bin/env python3
"""Join the frozen 18-hour multi-city outcome, market, and GEFS layers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.features.multicity_model_ready import (
    aggregate_gefs_messages,
    ordered_bucket_thresholds,
)
from weather_quant.ingestion.polymarket_price_history import parse_utc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("immutable output exists")
    config = json.loads(args.config.read_text())
    inventory_document = json.loads(Path(config["source_inventory"]).read_text())
    inventory = {str(row["event_id"]): row for row in inventory_document["rows"]}
    price_rows = [
        json.loads(line)
        for line in Path(config["source_price_horizons"]).read_text().splitlines()
    ]
    prices = {
        str(row["event_id"]): row
        for row in price_rows
        if row["horizon_hours"] == config["join_contract"]["horizon_hours"]
        and row["usable_full_vector"]
    }
    mapping_document = json.loads(Path(config["source_station_mapping"]).read_text())
    mappings = {
        str(row["event_id"]): row
        for row in mapping_document["rows"]
        if row["admitted"]
    }
    horizon_rows = [
        json.loads(line)
        for line in Path(config["source_gefs_horizons"]).read_text().splitlines()
    ]
    horizons = {
        str(row["event_id"]): row
        for row in horizon_rows
        if row["horizon_hours"] == config["join_contract"]["horizon_hours"]
        and row["complete_admissible"]
    }
    message_rows = [
        json.loads(line)
        for line in Path(config["source_gefs_messages"]).read_text().splitlines()
    ]
    messages: dict[str, list[dict]] = defaultdict(list)
    for row in message_rows:
        messages[str(row["event_id"])].append(row)

    event_ids = sorted(set(prices) & set(mappings) & set(horizons) & set(messages))
    rows = []
    exclusions = []
    leakage_count = 0
    message_mismatch_count = 0
    winner_anomaly_count = 0
    normalization_errors = []
    for event_id in event_ids:
        event = inventory[event_id]
        price = prices[event_id]
        mapping = mappings[event_id]
        horizon = horizons[event_id]
        event_messages = messages[event_id]
        if len(event_messages) != horizon["expected_pair_count"]:
            message_mismatch_count += 1
            exclusions.append({"event_id": event_id, "reason": "MESSAGE_COUNT_MISMATCH"})
            continue
        if any(row["status"] != "SUCCESS" for row in event_messages):
            exclusions.append({"event_id": event_id, "reason": "MESSAGE_FAILURE"})
            continue
        cutoff = parse_utc(price["cutoff_utc"])
        late = any(parse_utc(row["published_at_utc"]) > cutoff for row in event_messages)
        leakage_count += int(late)
        buckets = ordered_bucket_thresholds(event["buckets"], event["temperature_unit"])
        winners = [index for index, bucket in enumerate(buckets) if bucket["terminal_yes_winner"]]
        if len(winners) != 1:
            winner_anomaly_count += 1
            exclusions.append({"event_id": event_id, "reason": "WINNER_COUNT_ANOMALY"})
            continue
        market_by_id = {str(point["market_id"]): point for point in price["points"]}
        if set(market_by_id) != {str(bucket["market_id"]) for bucket in buckets}:
            exclusions.append({"event_id": event_id, "reason": "MARKET_IDENTITY_MISMATCH"})
            continue
        raw = [float(market_by_id[str(bucket["market_id"])]["price"]) for bucket in buckets]
        raw_sum = math.fsum(raw)
        if raw_sum <= 0:
            exclusions.append({"event_id": event_id, "reason": "NONPOSITIVE_MARKET_SUM"})
            continue
        normalized = [value / raw_sum for value in raw]
        normalization_error = abs(math.fsum(normalized) - 1.0)
        normalization_errors.append(normalization_error)
        bucket_rows = []
        for bucket, raw_price, probability in zip(buckets, raw, normalized):
            bucket_rows.append(
                {
                    **bucket,
                    "market_price_raw": raw_price,
                    "market_probability_normalized": probability,
                }
            )
        rows.append(
            {
                "event_id": event_id,
                "city": event["city"],
                "station_code": mapping["station_code"],
                "latitude": mapping["latitude"],
                "longitude": mapping["longitude"],
                "target_date": event["target_date"],
                "temperature_unit": event["temperature_unit"],
                "decision_time_utc": price["cutoff_utc"],
                "winner_index": winners[0],
                "winner_market_id": buckets[winners[0]]["market_id"],
                "market_raw_probability_sum": raw_sum,
                "market_max_staleness_seconds": price["maximum_staleness_seconds"],
                "bucket_count": len(buckets),
                "buckets": bucket_rows,
                **aggregate_gefs_messages(event_messages),
                "gefs_exact_partition": horizon["exact_partition"],
                "gefs_outside_local_seconds": horizon["outside_local_seconds"],
                "gefs_message_count": len(event_messages),
            }
        )

    numeric_values = []
    required_missing = 0
    for row in rows:
        required = (
            "event_id",
            "city",
            "station_code",
            "target_date",
            "decision_time_utc",
            "winner_index",
            "gefs_overlap_mean_max_f",
            "gefs_overlap_spread_at_mean_max_f",
            "gefs_max_block_spread_f",
        )
        required_missing += sum(row.get(field) is None for field in required)
        numeric_values.extend(value for value in row.values() if isinstance(value, float))
        for bucket in row["buckets"]:
            numeric_values.extend(value for value in bucket.values() if isinstance(value, float))
    duplicate_count = len(rows) - len({row["event_id"] for row in rows})
    nonfinite_count = sum(not math.isfinite(value) for value in numeric_values)
    summary = {
        "candidate_event_count": len(event_ids),
        "joined_event_count": len(rows),
        "joined_city_count": len({row["city"] for row in rows}),
        "excluded_event_count": len(exclusions),
        "duplicate_event_count": duplicate_count,
        "missing_required_field_count": required_missing,
        "nonfinite_numeric_count": nonfinite_count,
        "temporal_leakage_count": leakage_count,
        "winner_count_anomaly": winner_anomaly_count,
        "maximum_market_normalization_error": max(normalization_errors, default=math.inf),
        "forecast_message_count_mismatch": message_mismatch_count,
        "exact_partition_event_count": sum(row["gefs_exact_partition"] for row in rows),
        "overlap_proxy_event_count": sum(not row["gefs_exact_partition"] for row in rows),
    }
    gates = config["quality_gates"]
    checks = {
        "exact_joined_event_count": len(rows) == gates["exact_joined_event_count"],
        "exact_joined_city_count": summary["joined_city_count"] == gates["exact_joined_city_count"],
        "maximum_duplicate_event_count": duplicate_count <= gates["maximum_duplicate_event_count"],
        "maximum_missing_required_field_count": required_missing
        <= gates["maximum_missing_required_field_count"],
        "maximum_nonfinite_numeric_count": nonfinite_count
        <= gates["maximum_nonfinite_numeric_count"],
        "maximum_temporal_leakage_count": leakage_count
        <= gates["maximum_temporal_leakage_count"],
        "maximum_winner_count_anomaly": winner_anomaly_count
        <= gates["maximum_winner_count_anomaly"],
        "maximum_market_normalization_error": summary["maximum_market_normalization_error"]
        <= gates["maximum_market_normalization_error"],
        "maximum_forecast_message_count_mismatch": message_mismatch_count
        <= gates["maximum_forecast_message_count_mismatch"],
    }
    rows.sort(key=lambda row: (row["target_date"], row["city"], row["event_id"]))
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "provenance": {
            key: {"path": config[key], "sha256": sha256(Path(config[key]))}
            for key in (
                "source_inventory",
                "source_price_horizons",
                "source_station_mapping",
                "source_gefs_messages",
                "source_gefs_horizons",
            )
        },
        "config_sha256": sha256(args.config),
        "summary": summary,
        "checks": checks,
        "decision": (
            "MODEL_READY_DATASET_PASS"
            if all(checks.values())
            else "MODEL_READY_DATASET_FAIL"
        ),
        "exclusions": exclusions,
        "rows_sha256": canonical_sha256(rows),
        "rows": rows,
        "boundary": config["boundary"],
    }
    args.output.parent.mkdir(parents=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
