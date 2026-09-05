#!/usr/bin/env python3
"""Fetch immutable NOAA/Gamma evidence and settle the frozen KORD paper decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib.request import Request, urlopen


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_json(url: str) -> tuple[dict, dict]:
    requested = datetime.now(timezone.utc)
    request = Request(url, headers={"User-Agent": "weather-quant/0.1 abdullahsezdi@gmail.com"})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        metadata = {
            "url": url,
            "http_status": response.status,
            "content_type": response.headers.get("Content-Type"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "requested_at_utc": requested.isoformat().replace("+00:00", "Z"),
            "received_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
    return json.loads(body), metadata


def noaa_maximum_f(payload: dict) -> tuple[int, list[dict]]:
    observations = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        temperature = properties.get("temperature") or {}
        value_c = temperature.get("value")
        if value_c is None:
            continue
        value_f = Decimal(str(value_c)) * Decimal(9) / Decimal(5) + Decimal(32)
        rounded_f = int(value_f.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        observations.append(
            {
                "timestamp": properties.get("timestamp"),
                "temperature_c": value_c,
                "temperature_f": float(value_f),
                "rounded_temperature_f": rounded_f,
            }
        )
    if not observations:
        raise ValueError("NOAA returned no finite temperature observations")
    return max(row["rounded_temperature_f"] for row in observations), observations


def gamma_winner(payload: dict) -> dict:
    winners = []
    for market in payload.get("markets", []):
        prices = json.loads(market.get("outcomePrices") or "[]")
        if market.get("umaResolutionStatus") == "resolved" and prices == ["1", "0"]:
            winners.append(market)
    if len(winners) != 1:
        raise ValueError(f"expected exactly one resolved Gamma winner, found {len(winners)}")
    return winners[0]


def paper_bucket_for_temperature(rows: list[dict], temperature_f: int) -> dict:
    matches = [
        row
        for row in rows
        if (row["lower_bound"] is None or temperature_f >= row["lower_bound"])
        and (row["upper_bound"] is None or temperature_f <= row["upper_bound"])
    ]
    if len(matches) != 1:
        raise ValueError("paper bucket partition did not produce exactly one match")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.raw_directory.exists() or args.output.exists():
        raise FileExistsError("raw and processed outputs must be immutable")
    config = json.loads(args.config.read_text())
    paper_path = Path(config["paper_source"])
    if sha256_path(paper_path) != config["paper_source_sha256"]:
        raise ValueError("paper source checksum mismatch")
    paper = json.loads(paper_path.read_text())
    noaa, noaa_metadata = fetch_json(config["event"]["noaa_url"])
    gamma, gamma_metadata = fetch_json(config["event"]["gamma_url"])
    args.raw_directory.mkdir(parents=True)
    for name, payload, metadata in (
        ("noaa-observations", noaa, noaa_metadata),
        ("gamma-event", gamma, gamma_metadata),
    ):
        envelope = {"metadata": metadata, "payload": payload}
        (args.raw_directory / f"{name}.json").write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n"
        )
    maximum_f, observations = noaa_maximum_f(noaa)
    noaa_bucket = paper_bucket_for_temperature(paper["rows"], maximum_f)
    winner = gamma_winner(gamma)
    gamma_market_id = str(winner["id"])
    match = noaa_bucket["market_id"] == gamma_market_id
    selected = next(
        row
        for row in paper["rows"]
        if row["market_id"] == paper["paper_decisions"]["quantile"]["selected_market_id"]
    )
    hypothetical_cost = Decimal(selected["execution"]["requested_notional_usd"])
    hypothetical_fee = Decimal(selected["taker_fee_usd"])
    shares = Decimal(selected["execution"]["filled_shares"])
    won = selected["market_id"] == gamma_market_id
    payout = shares if won else Decimal(0)
    pnl = payout - hypothetical_cost - hypothetical_fee
    gates = config["gates"]
    checks = {
        "minimum_noaa_observations": len(observations)
        >= gates["minimum_noaa_temperature_observations"],
        "exactly_one_gamma_winner": True,
        "noaa_gamma_bucket_match": match,
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "champion": config["champion"],
        "noaa": {
            "observation_count": len(observations),
            "maximum_rounded_f": maximum_f,
            "bucket_market_id": noaa_bucket["market_id"],
            "bucket_label": noaa_bucket["label"],
        },
        "gamma": {
            "winner_market_id": gamma_market_id,
            "winner_label": winner["groupItemTitle"],
        },
        "checks": checks,
        "decision": "SETTLEMENT_RECONCILIATION_PASS" if all(checks.values()) else "QUARANTINE",
        "frozen_paper_results": {
            "gaussian": {"decision": "NO_TRADE", "paper_pnl_usd": "0"},
            "quantile": {
                "decision": "PAPER_TRADE",
                "won": won,
                "cost_usd": str(hypothetical_cost),
                "fee_usd": str(hypothetical_fee),
                "payout_usd": str(payout),
                "paper_pnl_usd": str(pnl),
            },
        },
        "raw_directory": str(args.raw_directory),
        "trading_authorized": False,
    }
    args.output.parent.mkdir(parents=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not all(checks.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
