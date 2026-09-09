#!/usr/bin/env python3
"""Collect immutable 18-hour price histories for the frozen US NBM pilot."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.probe_multicity_price_horizons import fetch_token, sha256_path, utc_now
from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.ingestion.multicity_price_horizon import (
    event_horizon_coverage,
    summarize_horizons,
)
from weather_quant.ingestion.polymarket_price_history import parse_utc, validate_history


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"immutable output exists: {args.output}")

    config = json.loads(args.config.read_text())
    selected_path = args.selection / "selected-events.json"
    selected = json.loads(selected_path.read_text())
    inventory = json.loads(Path(config["source_inventory"]).read_text())
    selected_ids = {str(event["event_id"]) for event in selected}
    raw_lookup = {
        str(event["id"]): event
        for event, _ in iter_raw_events(Path(inventory["source_manifest"]["directory"]))
        if str(event.get("id")) in selected_ids
    }
    if set(raw_lookup) != selected_ids:
        raise ValueError("selected events missing from frozen raw source")

    tokens = []
    for event in selected:
        raw = raw_lookup[str(event["event_id"])]
        start_ts = int(parse_utc(str(raw["creationDate"])).timestamp())
        end_ts = int(parse_utc(str(event["end_date_utc"])).timestamp())
        for bucket in event["buckets"]:
            tokens.append(
                {
                    "event_id": event["event_id"],
                    "market_id": bucket["market_id"],
                    "yes_token_id": bucket["yes_token_id"],
                    "request_start_ts": start_ts,
                    "request_end_ts": end_ts,
                }
            )
    expected_requests = sum(len(event["buckets"]) for event in selected)
    if len(tokens) != expected_requests:
        raise ValueError("token request construction mismatch")

    args.output.mkdir(parents=True)
    response_dir = args.output / "responses"
    response_dir.mkdir()
    responses = [None] * len(tokens)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_token, token, config["price_history"]): index
            for index, token in enumerate(tokens)
        }
        for future in as_completed(futures):
            index = futures[future]
            envelope = future.result()
            responses[index] = envelope
            (response_dir / f"token-{index:04d}.json").write_text(
                json.dumps(envelope, indent=2, sort_keys=True) + "\n"
            )

    histories = {}
    diagnostics = []
    for response in responses:
        if response is None:
            raise ValueError("missing in-memory response envelope")
        request_ok = False
        history = []
        error = None
        try:
            history = json.loads(response["body_text"])["history"]
            validation = validate_history(
                history, response["request_start_ts"], response["request_end_ts"]
            )
            request_ok = response["http_status"] == 200
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            validation = {"point_count": 0}
            error = f"{type(exc).__name__}: {exc}"
        if request_ok:
            histories[str(response["yes_token_id"])] = history
        diagnostics.append(
            {
                key: response[key]
                for key in ("event_id", "market_id", "yes_token_id", "http_status")
            }
            | {"request_ok": request_ok, "parse_error": error}
            | validation
        )

    horizon_rows = []
    for event in selected:
        horizon_rows.extend(
            event_horizon_coverage(
                event,
                histories,
                [config["join_contract"]["market_horizon_hours_before_end"]],
                config["price_history"]["maximum_staleness_seconds"],
            )
        )
    horizon_summary = summarize_horizons(horizon_rows)
    horizon = str(config["join_contract"]["market_horizon_hours_before_end"])
    usable_rate = horizon_summary["by_horizon"][horizon]["usable_full_vector_event_rate"]
    request_errors = sum(not row["request_ok"] for row in diagnostics)
    leakage_count = sum(
        point["timestamp"] > int(parse_utc(row["cutoff_utc"]).timestamp())
        for row in horizon_rows
        for point in row["points"]
    )
    usable_rows = [row for row in horizon_rows if row["usable_full_vector"]]
    usable_by_city = Counter(str(row["city"]) for row in usable_rows)
    usable_dates = {str(row["target_date"]) for row in usable_rows}
    minimum_usable_events_per_city = min(usable_by_city.values(), default=0)
    summary = {
        "selected_event_count": len(selected),
        "token_request_count": len(tokens),
        "request_error_count": request_errors,
        "request_error_rate": request_errors / len(tokens),
        "complete_vector_event_count": horizon_summary["by_horizon"][horizon][
            "complete_vector_event_count"
        ],
        "usable_full_vector_event_count": horizon_summary["by_horizon"][horizon][
            "usable_full_vector_event_count"
        ],
        "usable_full_vector_event_rate": usable_rate,
        "city_count_with_usable_vector": horizon_summary["by_horizon"][horizon][
            "city_count_with_usable_vector"
        ],
        "usable_date_count": len(usable_dates),
        "minimum_usable_events_per_city": minimum_usable_events_per_city,
        "usable_event_count_by_city": dict(sorted(usable_by_city.items())),
        "temporal_leakage_count": leakage_count,
    }
    gates = config["acceptance_thresholds"]
    checks = {
        "exact_selected_event_count": len(selected)
        == gates.get("exact_selected_event_count", len(selected)),
        "exact_token_request_count": len(tokens)
        == gates.get("exact_token_request_count", len(tokens)),
        "minimum_usable_full_vector_event_count": len(usable_rows)
        >= gates.get("minimum_usable_full_vector_event_count", 0),
        "minimum_complete_market_vector_rate": usable_rate
        >= gates["minimum_complete_market_vector_rate"],
        "minimum_usable_date_count": len(usable_dates)
        >= gates.get("minimum_usable_date_count", 0),
        "exact_city_count_with_usable_vector": len(usable_by_city)
        == gates.get("exact_city_count_with_usable_vector", len(usable_by_city)),
        "minimum_usable_events_per_city": minimum_usable_events_per_city
        >= gates.get("minimum_usable_events_per_city", 0),
        "maximum_request_error_count": request_errors
        <= gates.get("maximum_request_error_count", request_errors),
        "maximum_temporal_leakage_count": leakage_count
        <= gates["maximum_temporal_leakage_count"],
    }
    (args.output / "token-diagnostics.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in diagnostics)
    )
    (args.output / "event-horizon-coverage.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in horizon_rows)
    )
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "stage": "market_price_collection",
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "selected_events_sha256": sha256_path(selected_path),
        "summary": summary,
        "checks": checks,
        "decision": (
            "MARKET_PRICE_COLLECTION_PASS"
            if all(checks.values())
            else "MARKET_PRICE_COLLECTION_FAIL"
        ),
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
