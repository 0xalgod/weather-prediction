#!/usr/bin/env python3
"""Measure a locked daily GEFS representative-member coverage window."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from weather_quant.ingestion.noaa_gefs import (
    REQUIRED_FIELDS,
    fetch_index_summary,
    member_names,
    object_url,
)

REPRESENTATIVE_MEMBERS = ("gec00", "gep01", "gep30")
ALTERNATIVE_CYCLES = (6, 12, 18)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--cycle", type=int, default=0)
    parser.add_argument("--step", type=int, default=24)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def is_complete(probe: dict) -> bool:
    return probe["inventory"] is not None and probe["inventory"][
        "required_field_counts"
    ] == {field: 1 for field in REQUIRED_FIELDS}


def run_probe(run_date: str, cycle: int, member: str, step: int) -> tuple[str, str, dict]:
    return (
        run_date,
        member,
        fetch_index_summary(object_url(run_date, cycle, member, step)),
    )


def parallel_probe(
    requests: list[tuple[str, int, str, int]], workers: int
) -> dict[str, dict[str, dict]]:
    results: dict[str, dict[str, dict]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_probe, *request): request for request in requests}
        for future in as_completed(futures):
            run_date, member, probe = future.result()
            results.setdefault(run_date, {})[member] = probe
    return results


def main() -> None:
    args = parse_args()
    if args.days != 365:
        raise ValueError("this pre-registered probe requires exactly 365 days")
    dates = [args.start_date + timedelta(days=offset) for offset in range(args.days)]
    date_keys = [value.strftime("%Y%m%d") for value in dates]
    requests = [
        (run_date, args.cycle, member, args.step)
        for run_date in date_keys
        for member in REPRESENTATIVE_MEMBERS
    ]
    daily = parallel_probe(requests, args.workers)
    missing_dates = [
        run_date
        for run_date in date_keys
        if not all(is_complete(daily[run_date][member]) for member in REPRESENTATIVE_MEMBERS)
    ]

    diagnostics = {}
    if missing_dates:
        full_member_requests = [
            (run_date, args.cycle, member, args.step)
            for run_date in missing_dates
            for member in member_names()
        ]
        alternative_requests = [
            (run_date, cycle, member, args.step)
            for run_date in missing_dates
            for cycle in ALTERNATIVE_CYCLES
            for member in REPRESENTATIVE_MEMBERS
        ]
        diagnostics = {
            "primary_cycle_full_membership": parallel_probe(
                full_member_requests, args.workers
            ),
            "alternative_cycles_representative_members": {
                f"{run_date}-{cycle:02d}Z": parallel_probe(
                    [(run_date, cycle, member, args.step) for member in REPRESENTATIVE_MEMBERS],
                    args.workers,
                )[run_date]
                for run_date in missing_dates
                for cycle in ALTERNATIVE_CYCLES
            },
        }

    complete_probe_count = sum(
        is_complete(probe) for members in daily.values() for probe in members.values()
    )
    expected_probe_count = args.days * len(REPRESENTATIVE_MEMBERS)
    transport_failure_count = sum(
        any(error["kind"] == "transport" for error in probe["errors"])
        for members in daily.values()
        for probe in members.values()
    )
    artifact = {
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "noaa-gefs-daily-representative-coverage",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {"bucket": "noaa-gefs-pds", "product": "pgrb2sp25"},
        "request": {
            "start_date": args.start_date.isoformat(),
            "end_date": dates[-1].isoformat(),
            "days": args.days,
            "cycle": args.cycle,
            "step": args.step,
            "representative_members": list(REPRESENTATIVE_MEMBERS),
        },
        "pre_registered_acceptance": {
            "representative_coverage_minimum": 0.99,
            "required_fields_per_probe": {field: 1 for field in REQUIRED_FIELDS},
            "transport_failures_after_retries": 0,
            "missing_date_diagnostic": "all 31 primary members and c00/p01/p30 at 06/12/18Z",
        },
        "summary": {
            "expected_probe_count": expected_probe_count,
            "complete_probe_count": complete_probe_count,
            "coverage": complete_probe_count / expected_probe_count,
            "complete_date_count": args.days - len(missing_dates),
            "missing_date_count": len(missing_dates),
            "missing_dates": missing_dates,
            "transport_failure_count": transport_failure_count,
            "representative_gate_passed": (
                complete_probe_count / expected_probe_count >= 0.99
                and transport_failure_count == 0
            ),
        },
        "limitation": (
            "Three members measure representative daily continuity; they do not prove "
            "that all 31 members were complete on every date."
        ),
        "daily": daily,
        "missing_date_diagnostics": diagnostics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"immutable artifact exists: {args.output}")
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), **artifact["summary"]}, indent=2))


if __name__ == "__main__":
    main()
