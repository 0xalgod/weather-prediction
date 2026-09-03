#!/usr/bin/env python3
"""Measure pre-registered historical CLOB price coverage for closed Chicago events."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.ingestion.polymarket_price_history import (
    parse_utc,
    select_events,
    summarize_coverage,
    validate_history,
    yes_token_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def iter_events(raw_directory: Path) -> Iterable[Mapping[str, Any]]:
    for event, _ in iter_raw_events(raw_directory):
        yield event


def fetch_one(
    row_index: int, row: Mapping[str, Any], settings: Mapping[str, Any], timeout: int
) -> tuple[int, dict[str, Any], bytes]:
    params = urllib.parse.urlencode(
        {
            "market": row["yes_token_id"],
            "startTs": row["request_start_ts"],
            "endTs": row["request_end_ts"],
            "interval": settings["interval"],
            "fidelity": settings["fidelity_minutes"],
        }
    )
    url = f"{settings['endpoint']}?{params}"
    started = utc_now()
    status = None
    error = None
    body = b""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        error = f"HTTPError: {exc.code}"
    except (urllib.error.URLError, TimeoutError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    envelope = {
        "retrieved_started_at_utc": started,
        "retrieved_finished_at_utc": utc_now(),
        "request_url": url,
        "http_status": status,
        "error": error,
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "body_text": body.decode("utf-8", errors="replace"),
    }
    return row_index, envelope, body


def main() -> int:
    args = parse_args()
    if args.run_directory.exists():
        raise FileExistsError(f"run directory already exists: {args.run_directory}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    raw_directory = Path(config["source_inventory_run"])
    cutoff = parse_utc(config["data_cutoff_utc"])
    limit = int(config["sample_selection"]["maximum_events"])
    selected = select_events(iter_events(raw_directory), cutoff, limit)
    token_rows = yes_token_rows(selected)
    args.run_directory.mkdir(parents=True)
    raw_responses = args.run_directory / "responses"
    raw_responses.mkdir()
    (args.run_directory / "selected-events.json").write_text(
        json.dumps(
            [
                {k: event.get(k) for k in ("id", "title", "creationDate", "endDate", "closedTime")}
                for event in selected
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    results = [None] * len(token_rows)
    settings = config["price_history"]
    timeout = int(settings["request_timeout_seconds"])
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(fetch_one, index, row, settings, timeout)
            for index, row in enumerate(token_rows)
        ]
        for future in as_completed(futures):
            index, envelope, body = future.result()
            (raw_responses / f"token-{index:04d}.json").write_text(
                json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            row = dict(token_rows[index])
            try:
                payload = json.loads(body) if body else None
                request_ok = envelope["http_status"] == 200 and isinstance(payload, dict)
                diagnostics = (
                    validate_history(
                        payload.get("history"), row["request_start_ts"], row["request_end_ts"]
                    )
                    if request_ok
                    else {"point_count": 0}
                )
            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                request_ok = False
                diagnostics = {"point_count": 0, "parse_error": f"{type(exc).__name__}: {exc}"}
            results[index] = {
                **row,
                "request_ok": request_ok,
                "http_status": envelope["http_status"],
                **diagnostics,
            }
            time.sleep(0.01)

    coverage_path = args.run_directory / "coverage.jsonl"
    coverage_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results), encoding="utf-8"
    )
    summary = summarize_coverage(
        results, int(config["acceptance_thresholds"]["minimum_points_per_covered_token"])
    )
    thresholds = config["acceptance_thresholds"]
    checks = {
        "minimum_selected_events": summary["selected_event_count"]
        >= thresholds["minimum_selected_events"],
        "minimum_events_with_any_history_rate": summary["events_with_any_history_rate"]
        >= thresholds["minimum_events_with_any_history_rate"],
        "minimum_tokens_with_any_history_rate": summary["tokens_with_any_history_rate"]
        >= thresholds["minimum_tokens_with_any_history_rate"],
        "maximum_request_error_rate": summary["request_error_rate"]
        <= thresholds["maximum_request_error_rate"],
        "maximum_out_of_window_point_rate": summary["out_of_window_point_rate"]
        <= thresholds["maximum_out_of_window_point_rate"],
        "minimum_points_per_covered_token": summary["covered_tokens_meeting_minimum_rate"] == 1.0,
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config": config,
        "run_directory": str(args.run_directory),
        "summary": summary,
        "checks": checks,
        "decision": "HISTORICAL_PRICE_COVERAGE_PASS"
        if all(checks.values())
        else "HISTORICAL_PRICE_COVERAGE_FAIL",
        "interpretation_boundary": (
            "Indicative timestamp-price history only; no historical L2 bid/ask, depth, "
            "spread, side, size or fill evidence."
        ),
    }
    (args.run_directory / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
