#!/usr/bin/env python3
"""Build the locked 114-date Chicago NBM calibration dataset."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from weather_quant.features.historical_join import (
    exact_target_record,
    select_chicago_date_range,
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
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def download_with_retries(
    identity: dict[str, Any], raw_directory: Path, cycle: int, policy: dict[str, Any]
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]]]:
    run_date = identity["forecast_run_date"]
    attempts = []
    accepted = None
    retryable = set(policy["retryable_errors"])
    for attempt_number in range(1, int(policy["maximum_attempts_per_object"]) + 1):
        destination = raw_directory / (
            f"blend.{run_date}.t{cycle:02d}z.attempt-{attempt_number:02d}.nbptx"
        )
        try:
            accepted = download_public_object(
                probabilistic_text_url(run_date, cycle),
                destination,
                timeout=float(policy["timeout_seconds"]),
            )
            attempts.append(
                {
                    "attempt": attempt_number,
                    "status": "ACCEPTED",
                    "local_path": str(destination),
                    "sha256": accepted["sha256"],
                }
            )
            break
        except Exception as exc:  # retain every partial attempt, never parse it
            error_type = type(exc).__name__
            attempts.append(
                {
                    "attempt": attempt_number,
                    "status": "FAILED_PARTIAL_NOT_ACCEPTED",
                    "local_path": str(destination),
                    "error_type": error_type,
                    "error": str(exc),
                }
            )
            if error_type not in retryable:
                break
    return identity["event_id"], accepted, attempts


def main() -> int:
    args = parse_args()
    if args.run_directory.exists():
        raise FileExistsError(f"immutable run path exists: {args.run_directory}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    universe = config["universe"]
    inventory = Path(universe["gamma_inventory"])
    events = select_chicago_date_range(
        (event for event, _ in iter_raw_events(inventory)),
        date.fromisoformat(universe["target_date_start"]),
        date.fromisoformat(universe["target_date_end"]),
    )
    if len(events) != int(universe["expected_event_count"]):
        raise ValueError(f"expected {universe['expected_event_count']} events, found {len(events)}")
    identities = [event["_join_identity"] for event in events]

    policy = config["retrieval"]
    reuse_path = Path(policy["reuse_source"])
    if sha256_path(reuse_path) != policy["reuse_source_sha256"]:
        raise ValueError("reuse result checksum mismatch")
    reused_result = json.loads(reuse_path.read_text(encoding="utf-8"))
    accepted: dict[str, dict[str, Any]] = {}
    provenance: dict[str, dict[str, Any]] = {}
    valid_run_dates = {identity["forecast_run_date"] for identity in identities}
    for row in reused_result["rows"]:
        retrieval = row.get("retrieval")
        if not retrieval or row["forecast_run_date"] not in valid_run_dates:
            continue
        source_path = Path(retrieval["local_path"])
        if not source_path.is_file() or sha256_path(source_path) != retrieval["sha256"]:
            raise ValueError(f"reuse object checksum mismatch: {source_path}")
        accepted[row["forecast_run_date"]] = retrieval
        provenance[row["forecast_run_date"]] = {
            "status": "REUSED_CHECKSUM_VERIFIED",
            "attempts": [],
        }

    raw_directory = args.run_directory / "nbm"
    raw_directory.mkdir(parents=True)
    cycle = int(config["forecast"]["cycle_utc"])
    pending = [identity for identity in identities if identity["forecast_run_date"] not in accepted]
    with ThreadPoolExecutor(max_workers=int(policy["workers"])) as executor:
        futures = [
            executor.submit(download_with_retries, identity, raw_directory, cycle, policy)
            for identity in pending
        ]
        for future in as_completed(futures):
            event_id, retrieval, attempts = future.result()
            identity = next(item for item in identities if item["event_id"] == event_id)
            run_date = identity["forecast_run_date"]
            if retrieval:
                accepted[run_date] = retrieval
            provenance[run_date] = {
                "status": "DOWNLOADED" if retrieval else "DOWNLOAD_FAILED",
                "attempts": attempts,
            }

    rows = []
    for identity in identities:
        run_date = identity["forecast_run_date"]
        retrieval = accepted.get(run_date)
        reasons = []
        forecast = None
        if retrieval is None:
            reasons.append("FORECAST_OBJECT_UNAVAILABLE")
        else:
            last_modified = parsedate_to_datetime(retrieval["http_last_modified"]).astimezone(
                timezone.utc
            )
            decision_time = datetime.fromisoformat(
                identity["decision_time_utc"].replace("Z", "+00:00")
            )
            if last_modified > decision_time:
                reasons.append("PUBLICATION_PROXY_AFTER_DECISION")
            try:
                parsed = parse_station_maxt(
                    Path(retrieval["local_path"]),
                    config["forecast"]["station_code"],
                    f"{run_date[:4]}-{run_date[4:6]}-{run_date[6:]}T{cycle:02d}:00:00Z",
                )
                forecast = exact_target_record(parsed["records"], identity["target_valid_time_utc"])
                if forecast["nbm_version"] != config["forecast"]["nbm_version"]:
                    reasons.append("NBM_VERSION_MISMATCH")
            except Exception as exc:
                reasons.append(f"FORECAST_PARSE_OR_TARGET_ERROR:{type(exc).__name__}")
        rows.append(
            {
                **identity,
                "forecast_semantic_class": config["forecast"]["semantic_class"],
                "forecast": forecast,
                "retrieval": retrieval,
                "retrieval_provenance": provenance.get(run_date),
                "eligible": not reasons,
                "reasons": reasons,
            }
        )

    eligible = [row for row in rows if row["eligible"]]
    initial_train = int(config["walk_forward"]["initial_train_events"])
    summary = {
        "universe_event_count": len(rows),
        "reused_object_count": sum(
            item["status"] == "REUSED_CHECKSUM_VERIFIED" for item in provenance.values()
        ),
        "downloaded_object_count": sum(
            item["status"] == "DOWNLOADED" for item in provenance.values()
        ),
        "failed_object_count": sum(
            item["status"] == "DOWNLOAD_FAILED" for item in provenance.values()
        ),
        "eligible_event_count": len(eligible),
        "eligible_event_rate": len(eligible) / len(rows),
        "available_oos_event_count": max(0, len(eligible) - initial_train),
        "publication_proxy_leakage_count": sum(
            "PUBLICATION_PROXY_AFTER_DECISION" in row["reasons"] for row in rows
        ),
        "failure_reason_counts": {
            reason: sum(reason in row["reasons"] for row in rows)
            for reason in sorted({reason for row in rows for reason in row["reasons"]})
        },
        "accepted_source_bytes": sum(
            row["retrieval"]["byte_count"] for row in rows if row["retrieval"]
        ),
    }
    thresholds = config["acceptance_thresholds"]
    checks = {
        "expected_universe_count": len(rows) == universe["expected_event_count"],
        "eligible_event_rate_minimum": summary["eligible_event_rate"]
        >= thresholds["eligible_event_rate_minimum"],
        "oos_event_count_minimum": summary["available_oos_event_count"]
        >= thresholds["oos_event_count_minimum"],
        "publication_proxy_leakage_zero": summary["publication_proxy_leakage_count"] == 0,
    }
    result = {
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "generated_at_utc": utc_now(),
        "config": config,
        "summary": summary,
        "checks": checks,
        "decision": "CALIBRATION_DATASET_PASS"
        if all(checks.values())
        else "CALIBRATION_DATASET_FAIL",
        "rows": rows,
    }
    (args.run_directory / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
