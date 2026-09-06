#!/usr/bin/env python3
"""Retrieve immutable price histories and measure multi-city horizon coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.ingestion.multicity_price_horizon import (
    event_horizon_coverage,
    stratified_two_per_city,
    summarize_horizons,
)
from weather_quant.ingestion.polymarket_price_history import parse_utc, validate_history


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_token(token: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "market": token["yes_token_id"],
            "startTs": token["request_start_ts"],
            "endTs": token["request_end_ts"],
            "interval": settings["interval"],
            "fidelity": settings["fidelity_minutes"],
        }
    )
    url = f"{settings['endpoint']}?{params}"
    attempts = []
    body = b""
    status = None
    for attempt in range(1, int(settings["maximum_attempts"]) + 1):
        started = utc_now()
        error = None
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "weather-quant-research/0.1"}
            )
            with urllib.request.urlopen(
                request, timeout=int(settings["request_timeout_seconds"])
            ) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, body, error = exc.code, exc.read(), f"HTTPError: {exc.code}"
        except (urllib.error.URLError, TimeoutError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        attempts.append(
            {
                "attempt": attempt,
                "started_at_utc": started,
                "finished_at_utc": utc_now(),
                "http_status": status,
                "error": error,
                "content_sha256": hashlib.sha256(body).hexdigest(),
            }
        )
        if status == 200:
            break
        time.sleep(float(settings["retry_backoff_seconds"]) * attempt)
    return {
        **token,
        "request_url": url,
        "attempts": attempts,
        "http_status": status,
        "body_text": body.decode("utf-8", errors="replace"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"immutable output exists: {args.output}")

    config = json.loads(args.config.read_text())
    inventory_path = Path(config["source_inventory"])
    inventory = json.loads(inventory_path.read_text())
    research_cities = set(inventory["research_cities"])
    selected = stratified_two_per_city(inventory["rows"], research_cities)
    selected_ids = {str(row["event_id"]) for row in selected}
    source_directory = Path(inventory["source_manifest"]["directory"])
    raw_lookup = {
        str(event["id"]): event
        for event, _ in iter_raw_events(source_directory)
        if str(event.get("id")) in selected_ids
    }
    if set(raw_lookup) != selected_ids:
        raise ValueError("selected events missing from frozen raw source")

    tokens = []
    for event in selected:
        raw = raw_lookup[str(event["event_id"])]
        start_ts = int(parse_utc(str(raw["creationDate"])).timestamp())
        end_ts = int(parse_utc(str(raw["closedTime"])).timestamp())
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

    args.output.mkdir(parents=True)
    response_dir = args.output / "responses"
    response_dir.mkdir()
    (args.output / "selected-events.json").write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n"
    )
    responses: list[dict[str, Any] | None] = [None] * len(tokens)
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

    histories: dict[str, list[dict[str, Any]]] = {}
    diagnostics = []
    for response in responses:
        assert response is not None
        request_ok = False
        history: list[dict[str, Any]] = []
        error = None
        try:
            payload = json.loads(response["body_text"])
            history = payload["history"]
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
                config["horizons_hours_before_end_date"],
                config["full_vector_rule"]["maximum_staleness_seconds"],
            )
        )
    summary = summarize_horizons(horizon_rows)
    request_errors = sum(not row["request_ok"] for row in diagnostics)
    summary["selected_city_count"] = len({row["city"] for row in selected})
    summary["selected_event_count"] = len(selected)
    summary["token_request_count"] = len(diagnostics)
    summary["request_error_count"] = request_errors
    summary["request_error_rate"] = request_errors / len(diagnostics)
    summary["duplicate_selected_event_count"] = len(selected) - len(selected_ids)
    rates = [
        row["usable_full_vector_event_rate"] for row in summary["by_horizon"].values()
    ]
    thresholds = config["acceptance_thresholds"]
    checks = {
        "exact_selected_city_count": summary["selected_city_count"]
        == thresholds["exact_selected_city_count"],
        "exact_selected_event_count": summary["selected_event_count"]
        == thresholds["exact_selected_event_count"],
        "maximum_request_error_rate": summary["request_error_rate"]
        <= thresholds["maximum_request_error_rate"],
        "minimum_full_vector_event_rate_at_any_horizon": max(rates, default=0)
        >= thresholds["minimum_full_vector_event_rate_at_any_horizon"],
        "minimum_cities_with_full_vector_at_any_horizon": summary[
            "cities_with_usable_vector_at_any_horizon_count"
        ]
        >= thresholds["minimum_cities_with_full_vector_at_any_horizon"],
        "maximum_duplicate_selected_event_count": summary["duplicate_selected_event_count"]
        <= thresholds["maximum_duplicate_selected_event_count"],
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
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(args.config),
        "source_inventory_sha256": sha256_path(inventory_path),
        "summary": summary,
        "checks": checks,
        "decision": (
            "PRICE_HORIZON_PILOT_PASS"
            if all(checks.values())
            else "PRICE_HORIZON_PILOT_FAIL"
        ),
        "boundary": config["boundary"],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
