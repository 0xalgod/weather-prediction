#!/usr/bin/env python3
"""Build the pre-registered NBM and resolved-outcome Chicago join."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from weather_quant.features.historical_join import (
    event_join_identity,
    exact_target_record,
    index_events,
    sha256_path,
)
from weather_quant.ingestion.closed_market_audit import iter_raw_events
from weather_quant.ingestion.noaa_nbm import (
    download_public_object,
    parse_station_maxt,
    probabilistic_text_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def download_one(identity: dict[str, Any], raw_directory: Path, cycle: int):
    run_date = identity["forecast_run_date"]
    destination = raw_directory / f"blend.{run_date}.t{cycle:02d}z.nbptx"
    try:
        retrieval = download_public_object(
            probabilistic_text_url(run_date, cycle), destination, timeout=120
        )
        return identity["event_id"], retrieval, None
    except Exception as exc:  # preserve per-event failure instead of dropping denominator
        return identity["event_id"], None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    args = parse_args()
    if args.run_directory.exists():
        raise FileExistsError(f"immutable run path exists: {args.run_directory}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    selection_path = Path(config["event_selection"]["source"])
    if sha256_path(selection_path) != config["event_selection"]["source_sha256"]:
        raise ValueError("locked event selection checksum mismatch")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    expected_ids = [str(event["id"]) for event in selection]
    if len(expected_ids) != config["event_selection"]["expected_event_count"]:
        raise ValueError("locked event count mismatch")
    inventory = Path(config["event_selection"]["gamma_inventory"])
    events = index_events((event for event, _ in iter_raw_events(inventory)), expected_ids)
    identities = [event_join_identity(event) for event in events]

    raw_directory = args.run_directory / "nbm"
    raw_directory.mkdir(parents=True)
    cycle = int(config["forecast"]["cycle_utc"])
    downloads: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(download_one, item, raw_directory, cycle) for item in identities]
        for future in as_completed(futures):
            event_id, retrieval, error = future.result()
            downloads[event_id] = {"retrieval": retrieval, "error": error}

    joined = []
    for identity in identities:
        download = downloads[identity["event_id"]]
        row = {**identity, **download, "forecast": None, "eligible": False, "reasons": []}
        if download["error"]:
            row["reasons"].append("FORECAST_OBJECT_UNAVAILABLE")
        else:
            retrieval = download["retrieval"]
            last_modified = parsedate_to_datetime(retrieval["http_last_modified"]).astimezone(
                timezone.utc
            )
            decision_time = datetime.fromisoformat(
                identity["decision_time_utc"].replace("Z", "+00:00")
            )
            if last_modified > decision_time:
                row["reasons"].append("PUBLICATION_PROXY_AFTER_DECISION")
            try:
                parsed = parse_station_maxt(
                    Path(retrieval["local_path"]),
                    config["forecast"]["station_code"],
                    f"{identity['forecast_run_date'][:4]}-{identity['forecast_run_date'][4:6]}-"
                    f"{identity['forecast_run_date'][6:]}T{cycle:02d}:00:00Z",
                )
                row["forecast"] = exact_target_record(
                    parsed["records"], identity["target_valid_time_utc"]
                )
            except Exception as exc:
                row["reasons"].append(f"FORECAST_PARSE_OR_TARGET_ERROR:{type(exc).__name__}")
        row["eligible"] = not row["reasons"]
        joined.append(row)

    event_count = len(joined)
    retrieved = [row for row in joined if row["retrieval"] is not None]
    parsed = [row for row in retrieved if row["forecast"] is not None]
    eligible = [row for row in joined if row["eligible"]]
    leakage_count = sum("PUBLICATION_PROXY_AFTER_DECISION" in row["reasons"] for row in joined)
    summary = {
        "event_identity_match_count": event_count,
        "event_count": event_count,
        "forecast_object_count": len(retrieved),
        "forecast_object_rate": len(retrieved) / event_count,
        "forecast_parse_and_target_count": len(parsed),
        "forecast_parse_rate_of_retrieved": len(parsed) / len(retrieved) if retrieved else 0.0,
        "publication_proxy_leakage_count": leakage_count,
        "exact_winner_count": event_count,
        "valid_bucket_partition_count": event_count,
        "joined_eligible_count": len(eligible),
        "joined_row_rate": len(eligible) / event_count,
        "downloaded_bytes": sum(row["retrieval"]["byte_count"] for row in retrieved),
        "failure_reason_counts": {
            reason: sum(reason in row["reasons"] for row in joined)
            for reason in sorted({reason for row in joined for reason in row["reasons"]})
        },
    }
    thresholds = config["acceptance_thresholds"]
    checks = {
        "event_identity_match_rate": event_count / len(expected_ids)
        == thresholds["event_identity_match_rate"],
        "forecast_object_rate_minimum": summary["forecast_object_rate"]
        >= thresholds["forecast_object_rate_minimum"],
        "forecast_parse_rate_minimum": summary["forecast_parse_rate_of_retrieved"]
        >= thresholds["forecast_parse_rate_minimum"],
        "forecast_publication_leakage_count_maximum": leakage_count
        <= thresholds["forecast_publication_leakage_count_maximum"],
        "exact_target_record_rate_minimum": len(parsed) / len(retrieved)
        >= thresholds["exact_target_record_rate_minimum"],
        "exact_winner_rate_minimum": summary["exact_winner_count"] / event_count
        >= thresholds["exact_winner_rate_minimum"],
        "bucket_partition_rate_minimum": summary["valid_bucket_partition_count"] / event_count
        >= thresholds["bucket_partition_rate_minimum"],
        "joined_row_rate_minimum": summary["joined_row_rate"]
        >= thresholds["joined_row_rate_minimum"],
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config": config,
        "summary": summary,
        "checks": checks,
        "decision": "HISTORICAL_JOIN_PASS" if all(checks.values()) else "HISTORICAL_JOIN_FAIL",
        "rows": joined,
        "limitations": [
            "HTTP Last-Modified is a retrospective publication proxy, not measured "
            "historical first-seen time.",
            "NBM target-valid-time to Chicago local-day mapping remains provisional.",
            "Historical CLOB prices are sparse and non-executable.",
        ],
    }
    (args.run_directory / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: result[key] for key in result if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
