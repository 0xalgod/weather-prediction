#!/usr/bin/env python3
"""Run one immutable, read-only KORD NBM-to-CLOB vertical slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weather_quant.ingestion.noaa_nbm import parse_station_maxt, probabilistic_text_url
from weather_quant.ingestion.polymarket_markets import write_raw_envelope
from weather_quant.ingestion.polymarket_orderbook import (
    fetch_book_envelope,
    fetch_tick_size_envelope,
    normalize_book,
    normalize_tick_size,
)
from weather_quant.market_model.vertical_slice import (
    ask_depth_vwap,
    gaussian_bucket_probabilities,
    taker_fee_usd,
)
from weather_quant.normalization.resolution_rules import build_bucket_records


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json_envelope(url: str, source: str, timeout: float = 30.0) -> dict[str, Any]:
    requested = utc_iso()
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "weather-quant-research/0.1"},
    )
    started = monotonic()
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        status = response.status
    return {
        "schema_version": "1.0.0",
        "source": source,
        "endpoint": url,
        "requested_at_utc": requested,
        "received_at_utc": utc_iso(),
        "retrieval_seconds": monotonic() - started,
        "http_status": status,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "payload": json.loads(raw),
    }


def fetch_fee_envelope(token_id: str) -> dict[str, Any]:
    url = "https://clob.polymarket.com/fee-rate?" + urlencode({"token_id": token_id})
    envelope = fetch_json_envelope(url, "polymarket_clob_fee_rate")
    envelope["token_id_requested"] = token_id
    return envelope


def retrieve_latest_nbm(
    raw_directory: Path, maximum_cycles: int
) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    attempts = []
    for offset in range(maximum_cycles):
        run = start - timedelta(hours=offset)
        url = probabilistic_text_url(run.strftime("%Y%m%d"), run.hour)
        path = raw_directory / f"nbm-{run:%Y%m%dT%HZ}.txt"
        requested_at = utc_iso()
        try:
            request = Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
            with urlopen(request, timeout=60) as response:
                raw = response.read()
                headers = dict(response.headers.items())
                status = response.status
        except HTTPError as error:
            attempts.append(
                {"run_time_utc": run.isoformat(), "url": url, "status": error.code}
            )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        manifest = {
            "source": "noaa_nbm_aws_public",
            "url": url,
            "model_run_time_utc": run.isoformat().replace("+00:00", "Z"),
            "requested_at_utc": requested_at,
            "received_at_utc": utc_iso(),
            "http_status": status,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "http_last_modified": headers.get("Last-Modified"),
            "http_etag": headers.get("ETag"),
            "local_path": str(path),
        }
        attempts.append(
            {"run_time_utc": manifest["model_run_time_utc"], "url": url, "status": status}
        )
        return path, manifest, attempts
    raise RuntimeError("no NBM cycle available inside registered backward search")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.raw_directory.exists() or args.output.exists():
        raise FileExistsError("run paths must be new and immutable")
    config = json.loads(args.config.read_text())
    identity_path = Path(config["identity_source"])
    identity_bytes = identity_path.read_bytes()
    if hashlib.sha256(identity_bytes).hexdigest() != config["identity_source_sha256"]:
        raise ValueError("identity source checksum mismatch")
    locked = next(
        row
        for row in json.loads(identity_bytes)["chicago_audits"]
        if row["event_id"] == config["event_id"]
    )

    args.raw_directory.mkdir(parents=True)
    nbm_path, nbm_manifest, cycle_attempts = retrieve_latest_nbm(
        args.raw_directory, config["forecast"]["maximum_cycles_checked"]
    )
    parsed = parse_station_maxt(
        nbm_path,
        config["station_code"],
        nbm_manifest["model_run_time_utc"],
    )
    candidates = [
        row
        for row in parsed["records"]
        if row["valid_time_utc"] == config["forecast"]["target_valid_time_utc"]
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one target NBM record, found {len(candidates)}")
    forecast = candidates[0]
    if forecast["mean_f"] is None or forecast["standard_deviation_f"] is None:
        raise ValueError("target NBM mean/std is missing")

    gamma_url = f"https://gamma-api.polymarket.com/events/{config['event_id']}"
    gamma = fetch_json_envelope(gamma_url, "polymarket_gamma_event")
    write_raw_envelope(gamma, args.raw_directory / "gamma-event.json")
    event = gamma["payload"]
    if str(event.get("id")) != config["event_id"]:
        raise ValueError("Gamma event ID mismatch")
    rule_hash = hashlib.sha256(event.get("description", "").encode()).hexdigest()
    if rule_hash != config["rule_text_sha256"]:
        raise ValueError("Gamma rule hash mismatch")
    buckets = build_bucket_records(event["markets"], "F")
    locked_by_market = {row["market_id"]: row for row in locked["token_identities"]}
    for bucket in buckets:
        expected = locked_by_market.get(bucket["market_id"])
        if expected is None or expected["condition_id"] != bucket["condition_id"]:
            raise ValueError("market/condition identity differs from locked source")
        if expected["token_ids"] != [bucket["yes_token_id"], bucket["no_token_id"]]:
            raise ValueError("token identity differs from locked source")
    if len(buckets) != config["expected_bucket_count"]:
        raise ValueError("bucket count differs from locked config")
    probabilities = gaussian_bucket_probabilities(
        buckets,
        forecast["mean_f"],
        forecast["standard_deviation_f"],
    )

    envelopes: dict[tuple[str, str], dict[str, Any]] = {}
    errors = {}
    with ThreadPoolExecutor(max_workers=11) as executor:
        futures = {}
        for bucket in buckets:
            token = bucket["yes_token_id"]
            futures[executor.submit(fetch_book_envelope, token)] = (token, "book")
            futures[executor.submit(fetch_tick_size_envelope, token)] = (token, "tick")
            futures[executor.submit(fetch_fee_envelope, token)] = (token, "fee")
        for future in as_completed(futures):
            key = futures[future]
            try:
                envelopes[key] = future.result()
            except Exception as error:  # preserve partial public-data failures
                errors["|".join(key)] = f"{type(error).__name__}: {error}"

    rows = []
    receipt_times = []
    notional = Decimal(str(config["execution"]["notional_usd_per_bucket"]))
    probability_by_token = {row["yes_token_id"]: row for row in probabilities}
    for token, probability_row in sorted(probability_by_token.items()):
        required = [(token, kind) for kind in ("book", "tick", "fee")]
        if any(key not in envelopes for key in required):
            rows.append({**probability_row, "execution_status": "METADATA_UNAVAILABLE"})
            continue
        book_envelope = envelopes[(token, "book")]
        tick_envelope = envelopes[(token, "tick")]
        fee_envelope = envelopes[(token, "fee")]
        for kind, envelope in (
            ("book", book_envelope),
            ("tick", tick_envelope),
            ("fee", fee_envelope),
        ):
            write_raw_envelope(envelope, args.raw_directory / f"{token}-{kind}.json")
        book = normalize_book(book_envelope, token)
        tick = normalize_tick_size(tick_envelope)
        receipt_times.append(datetime.fromisoformat(book["received_at_utc"].replace("Z", "+00:00")))
        execution = ask_depth_vwap(book["asks"], notional)
        base_fee_bps = Decimal(str(fee_envelope["payload"]["base_fee"]))
        endpoint_rate = base_fee_bps / Decimal("10000")
        gamma_market = next(
            market
            for market in event["markets"]
            if str(market["id"]) == probability_row["market_id"]
        )
        schedule = gamma_market.get("feeSchedule") or {}
        schedule_rate = Decimal(str(schedule.get("rate")))
        fee_rate_match = endpoint_rate == schedule_rate
        fee_usd = (
            taker_fee_usd(execution["fills"], endpoint_rate)
            if execution["executable"] and fee_rate_match
            else None
        )
        model_probability = Decimal(str(probability_row["model_probability"]))
        vwap = Decimal(execution["vwap"]) if execution["vwap"] is not None else None
        fee_per_share = (
            fee_usd / Decimal(execution["filled_shares"])
            if fee_usd is not None
            else None
        )
        gross_edge = model_probability - vwap if vwap is not None else None
        net_edge = (
            gross_edge - fee_per_share
            if gross_edge is not None and fee_per_share is not None
            else None
        )
        rows.append(
            {
                **probability_row,
                "book_quality": book["quality"],
                "book_received_at_utc": book["received_at_utc"],
                "tick_size": str(tick),
                "fee_base_bps": str(base_fee_bps),
                "fee_schedule_rate": str(schedule_rate),
                "fee_rate_match": fee_rate_match,
                "execution": execution,
                "taker_fee_usd": str(fee_usd) if fee_usd is not None else None,
                "gross_edge_per_share": str(gross_edge) if gross_edge is not None else None,
                "net_edge_per_share": str(net_edge) if net_edge is not None else None,
                "net_edge_after_1pp_haircut": str(net_edge - Decimal("0.01"))
                if net_edge is not None
                else None,
                "net_edge_after_2pp_haircut": str(net_edge - Decimal("0.02"))
                if net_edge is not None
                else None,
                "decision": "DIAGNOSTIC_ONLY",
            }
        )

    forecast_received = datetime.fromisoformat(
        nbm_manifest["received_at_utc"].replace("Z", "+00:00")
    )
    last_book = max(receipt_times) if receipt_times else None
    skew = (last_book - forecast_received).total_seconds() if last_book else None
    executable_count = sum(row.get("execution", {}).get("executable", False) for row in rows)
    probability_sum = sum(row["model_probability"] for row in probabilities)
    fee_match_all = all(row.get("fee_rate_match") is True for row in rows)
    checks = {
        "event_rule_identity": True,
        "bucket_count": len(buckets) == config["expected_bucket_count"],
        "probability_sum": abs(probability_sum - 1.0) <= 1e-9,
        "target_nbm_record": len(candidates) == 1,
        "forecast_precedes_books": last_book is not None and forecast_received <= last_book,
        "temporal_skew": skew is not None
        and skew <= config["execution"]["maximum_forecast_to_last_book_seconds"],
        "executable_coverage": executable_count
        >= config["execution"]["minimum_executable_bucket_count"],
        "fee_rate_reconciled": fee_match_all,
        "request_errors": not errors,
    }
    output = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "run_started_from_config": str(args.config),
        "forecast_manifest": nbm_manifest,
        "cycle_attempts": cycle_attempts,
        "forecast": forecast,
        "gamma_manifest": {key: gamma[key] for key in gamma if key != "payload"},
        "probability_model": config["forecast"]["probability_model"],
        "probability_sum": probability_sum,
        "forecast_to_last_book_seconds": skew,
        "bucket_count": len(buckets),
        "executable_bucket_count": executable_count,
        "request_errors": errors,
        "checks": checks,
        "decision": "VERTICAL_SLICE_MECHANICS_PASS"
        if all(checks.values())
        else "VERTICAL_SLICE_INCOMPLETE",
        "rows": rows,
        "raw_directory": str(args.raw_directory),
        "generated_at_utc": utc_iso(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "decision": output["decision"],
                "forecast": forecast,
                "bucket_count": len(buckets),
                "executable_bucket_count": executable_count,
                "probability_sum": probability_sum,
                "forecast_to_last_book_seconds": skew,
                "checks": checks,
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
