#!/usr/bin/env python3
"""Fetch read-only source snapshots and reconcile the fixed 20-event audit sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.request import Request, urlopen

from weather_quant.normalization.manual_reconciliation import (
    identity_matches,
    outcome_rule_check,
    parse_resolution_rule,
    parse_wunderground_high,
    terminal_winner,
)


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def fetch(url: str) -> bytes:
    request = Request(url, headers={"Accept": "*/*", "User-Agent": "weather-quant-research/0.1"})
    with urlopen(request, timeout=30) as response:  # nosec B310: URLs come from fixed sample/Gamma host
        return response.read()


def dated_source_url(source: str, end_date: str) -> str:
    date = end_date[:10]
    year, month, day = (int(part) for part in date.split("-"))
    return f"{source.rstrip('/')}/date/{year}-{month}-{day}"


def main() -> int:
    parsed = args()
    sample_doc = json.loads(parsed.sample.read_text(encoding="utf-8"))
    sample = sample_doc["manual_reconciliation_sample"]
    requests: Dict[Tuple[str, str], str] = {}
    for event in sample:
        event_id = event["event_id"]
        requests[(event_id, "gamma")] = f"https://gamma-api.polymarket.com/events/{event_id}"
        if event["resolution_source"]:
            requests[(event_id, "resolution_page")] = dated_source_url(event["resolution_source"], event["end_date"])

    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    bodies: Dict[Tuple[str, str], bytes] = {}
    errors: Dict[Tuple[str, str], str] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch, url): key for key, url in requests.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                bodies[key] = future.result()
            except Exception as error:  # preserve per-source failure instead of aborting the audit
                errors[key] = f"{type(error).__name__}: {error}"

    if parsed.output.exists() or parsed.raw_directory.exists():
        raise FileExistsError("output and raw directory must be new immutable paths")
    parsed.raw_directory.mkdir(parents=True)
    manifest = []
    for key, body in sorted(bodies.items()):
        event_id, kind = key
        suffix = "json" if kind == "gamma" else "html"
        destination = parsed.raw_directory / f"event-{event_id}-{kind}.{suffix}"
        destination.write_bytes(body)
        manifest.append({"event_id": event_id, "kind": kind, "url": requests[key], "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
    (parsed.raw_directory / "manifest.json").write_text(json.dumps({"retrieved_at_utc": retrieved_at, "files": manifest, "errors": {"|".join(k): v for k, v in errors.items()}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows = []
    for event in sample:
        event_id = event["event_id"]
        gamma_body = bodies.get((event_id, "gamma"))
        live = json.loads(gamma_body) if gamma_body else None
        rule = parse_resolution_rule(live.get("description", ""), live.get("resolutionSource")) if live else {}
        winner, terminal_status = terminal_winner(live.get("markets", [])) if live else (None, "GAMMA_FETCH_FAILED")
        page_body = bodies.get((event_id, "resolution_page"))
        observed_high = parse_wunderground_high(page_body.decode("utf-8", errors="replace")) if page_body else None
        identity_ok = identity_matches(event["markets"], live.get("markets", [])) if live else False
        outcome_check = outcome_rule_check(winner, observed_high)
        if not event["resolution_source"]:
            disposition = "NO_TRADE_MISSING_RESOLUTION_SOURCE"
        elif not identity_ok:
            disposition = "INVALID_IDENTIFIER_RECONCILIATION"
        elif terminal_status != "EXACT_TERMINAL_WINNER":
            disposition = "NON_TERMINAL_OR_CANCELLED"
        elif not observed_high:
            disposition = "INCONCLUSIVE_SOURCE_PAGE"
        elif outcome_check == "MATCH":
            disposition = "RECONCILED"
        elif outcome_check == "MISMATCH":
            disposition = "OUTCOME_SOURCE_MISMATCH_NO_TRADE"
        else:
            disposition = "INCONCLUSIVE_OUTCOME_RULE"
        rows.append({
            "event_id": event_id, "title": event["title"], "selection_stratum": event["selection_stratum"],
            "identity_match": identity_ok, "rule": rule, "terminal_winner_bucket": winner,
            "terminal_status": terminal_status, "observed_high_display": observed_high,
            "outcome_rule_check": outcome_check,
            "source_fetch_error": errors.get((event_id, "resolution_page")), "disposition": disposition,
        })

    output = {"schema_version": "0.1.0", "retrieved_at_utc": retrieved_at, "raw_manifest": str(parsed.raw_directory / "manifest.json"), "records": rows}
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    parsed.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(rows), "dispositions": {value: sum(x["disposition"] == value for x in rows) for value in sorted({x["disposition"] for x in rows})}, "fetch_errors": len(errors)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
