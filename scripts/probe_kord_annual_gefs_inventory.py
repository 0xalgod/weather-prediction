#!/usr/bin/env python3
"""Inventory all GEFS members and canonical KORD local-day TMAX objects."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from weather_quant.ingestion.noaa_gefs import (
    list_run_prefix,
    local_day_tmax_steps,
    member_names,
    object_url,
)

TIMEZONE = "America/Chicago"
EXPECTED_DAYS = 365


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-start", type=date.fromisoformat, required=True)
    parser.add_argument("--target-end", type=date.fromisoformat, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def dates_inclusive(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end date precedes start date")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def inventory_one(target: date, attempts: int) -> dict:
    run_date = target - timedelta(days=1)
    run_key = run_date.strftime("%Y%m%d")
    errors = []
    listing = None
    for attempt in range(1, attempts + 1):
        try:
            listing = list_run_prefix(run_key, cycle=0, timeout=90)
            break
        except (HTTPError, URLError, TimeoutError, ConnectionError) as error:
            errors.append(
                {"attempt": attempt, "kind": type(error).__name__, "detail": str(error)}
            )
            if attempt < attempts:
                time.sleep(0.5 * attempt)
    semantics = local_day_tmax_steps(target, TIMEZONE)
    if listing is None:
        return {
            "target_date": target.isoformat(),
            "run_date": run_key,
            "status": "LISTING_FAILED",
            "errors": errors,
            "semantics": semantics,
        }
    by_key = {item["key"]: item for item in listing["objects"]}
    required = []
    decision = datetime.combine(run_date, datetime.min.time(), tzinfo=timezone.utc).replace(
        hour=11
    )
    for member in member_names():
        member_complete = True
        objects = []
        for step in semantics["overlap_steps"]:
            url = object_url(run_key, 0, member, step)
            key = url.split(".com/", 1)[1]
            data = by_key.get(key)
            index = by_key.get(key + ".idx")
            data_published = (
                datetime.fromisoformat(data["last_modified"].replace("Z", "+00:00"))
                if data
                else None
            )
            index_published = (
                datetime.fromisoformat(index["last_modified"].replace("Z", "+00:00"))
                if index
                else None
            )
            complete = data is not None and index is not None
            publication_admissible = complete and max(data_published, index_published) <= decision
            member_complete = member_complete and complete and publication_admissible
            objects.append(
                {
                    "step": step,
                    "data": data,
                    "index": index,
                    "complete": complete,
                    "publication_admissible": publication_admissible,
                }
            )
        required.append(
            {"member": member, "complete_and_admissible": member_complete, "objects": objects}
        )
    return {
        "target_date": target.isoformat(),
        "run_date": run_key,
        "status": "INVENTORIED",
        "errors": errors,
        "semantics": semantics,
        "listing": {
            "prefix": listing["prefix"],
            "page_count": len(listing["pages"]),
            "pages": listing["pages"],
            "object_count": len(listing["objects"]),
        },
        "members": required,
    }


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError("GEFS inventory output must be immutable")
    targets = dates_inclusive(args.target_start, args.target_end)
    if len(targets) != EXPECTED_DAYS:
        raise ValueError("this contract requires exactly 365 target dates")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(inventory_one, target, args.attempts): target
            for target in targets
        }
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda item: item["target_date"])
    listing_failures = [row for row in rows if row["status"] != "INVENTORIED"]
    member_rows = [member for row in rows if "members" in row for member in row["members"]]
    objects = [
        obj
        for row in rows
        if "members" in row
        for member in row["members"]
        for obj in member["objects"]
    ]
    complete_members = sum(item["complete_and_admissible"] for item in member_rows)
    exact_dates = sum(row["semantics"]["exact_partition"] for row in rows)
    summary = {
        "target_date_count": len(rows),
        "listing_success_count": len(rows) - len(listing_failures),
        "listing_failure_count": len(listing_failures),
        "expected_member_day_count": EXPECTED_DAYS * len(member_names()),
        "observed_member_day_count": len(member_rows),
        "complete_admissible_member_day_count": complete_members,
        "complete_admissible_member_day_rate": complete_members
        / (EXPECTED_DAYS * len(member_names())),
        "required_data_index_pair_count": len(objects),
        "complete_data_index_pair_count": sum(item["complete"] for item in objects),
        "publication_admissible_pair_count": sum(
            item["publication_admissible"] for item in objects
        ),
        "exact_partition_date_count": exact_dates,
        "proxy_partition_date_count": len(rows) - exact_dates,
        "terminal_transport_failure_count": len(listing_failures),
    }
    summary["passed"] = (
        summary["complete_admissible_member_day_rate"] >= 0.97
        and summary["terminal_transport_failure_count"] == 0
    )
    artifact = {
        "schema_version": "1.0.0",
        "experiment_id": "EXP-20260905-kord-forecast-dataset-v1",
        "substep": "annual_gefs_full_member_inventory",
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "contract": {
            "target_start": args.target_start.isoformat(),
            "target_end": args.target_end.isoformat(),
            "timezone": TIMEZONE,
            "cycle_utc": 0,
            "member_count": len(member_names()),
            "required_parameter": "TMAX",
            "required_index_and_data_object": True,
            "decision_time": "run_date 11:00 UTC",
            "complete_admissible_member_day_rate_minimum": 0.97,
            "terminal_transport_failure_count_maximum": 0,
        },
        "summary": summary,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
