#!/usr/bin/env python3
"""Produce the registered fixture validation artifact for freeze snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from weather_quant.ingestion.freeze_snapshot import (
    build_freeze_snapshot,
    verify_freeze_snapshot,
    write_freeze_snapshot,
)

RULE_TEXT = "Synthetic KORD next-day-first-datapoint freeze rule."


def contract(**overrides) -> dict:
    value = {
        "event_id": "fixture-kord-20260901",
        "market_date_local": "2026-09-01",
        "station_code": "KORD",
        "station_name": "Chicago O'Hare Intl Airport Station",
        "timezone": "America/Chicago",
        "temperature_unit": "F",
        "rule_text": RULE_TEXT,
        "rule_text_sha256": hashlib.sha256(RULE_TEXT.encode()).hexdigest(),
        "rule_version": "fixture-v1",
        "parser_version": "wunderground-0.1.0",
    }
    value.update(overrides)
    return value


def retrieval(role: str, raw: bytes) -> dict:
    return {
        "url": f"https://example.test/{role}",
        "requested_at_utc": "2026-09-02T05:05:00Z",
        "received_at_utc": "2026-09-02T05:05:01Z",
        "http_status": 200,
        "raw": raw,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-fixture", type=Path, required=True)
    parser.add_argument("--trigger-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.target_fixture.read_bytes()
    trigger = args.trigger_fixture.read_bytes()

    def build(selected_contract: dict, selected_trigger: bytes, captured: str) -> dict:
        return build_freeze_snapshot(
            selected_contract,
            retrieval("target", target),
            retrieval("trigger", selected_trigger),
            captured,
        )

    valid = build(contract(), trigger, "2026-09-02T05:05:02Z")
    replay = build(contract(), trigger, "2026-09-02T05:05:02Z")
    empty_trigger = trigger.replace(b'[{"ts":1788325200,"temp":70}]', b"[]")
    cases = {
        "valid_fixture_qualifies": valid["freeze_eligible"],
        "deterministic_replay_same_snapshot_id": replay["snapshot_id"] == valid["snapshot_id"],
        "pre_midnight_fails_closed": not build(
            contract(), trigger, "2026-09-02T04:59:59Z"
        )["freeze_eligible"],
        "empty_trigger_fails_closed": not build(
            contract(), empty_trigger, "2026-09-02T05:05:02Z"
        )["freeze_eligible"],
        "station_mismatch_fails_closed": not build(
            contract(station_code="KAAA"), trigger, "2026-09-02T05:05:02Z"
        )["freeze_eligible"],
        "unit_mismatch_fails_closed": not build(
            contract(temperature_unit="C"), trigger, "2026-09-02T05:05:02Z"
        )["freeze_eligible"],
        "rule_hash_mismatch_fails_closed": not build(
            contract(rule_text_sha256="0" * 64), trigger, "2026-09-02T05:05:02Z"
        )["freeze_eligible"],
    }

    changed_target = target.replace("82°F".encode(), "83°F".encode()).replace(
        b'"temp":82', b'"temp":83'
    )
    changed = build_freeze_snapshot(
        contract(),
        retrieval("target", changed_target),
        retrieval("trigger", trigger),
        "2026-09-02T05:06:02Z",
    )
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        first_write = write_freeze_snapshot(root, valid, target, trigger)
        second_write = write_freeze_snapshot(root, valid, target, trigger)
        changed_write = write_freeze_snapshot(root, changed, changed_target, trigger)
        before_tamper = verify_freeze_snapshot(root, valid)
        raw_path = root / "raw" / "sha256" / f"{valid['target']['sha256']}.html"
        raw_path.write_bytes(b"tampered")
        after_tamper = verify_freeze_snapshot(root, valid)
        cases.update(
            {
                "first_write_appends": first_write["status"] == "APPENDED",
                "duplicate_write_is_idempotent": second_write["status"]
                == "IDEMPOTENT_REPLAY",
                "changed_content_appends_revision": changed_write["status"] == "APPENDED"
                and len(list((root / "manifests").glob("*.json"))) == 2,
                "checksum_verifies_before_tamper": before_tamper["all_valid"],
                "tamper_is_detected": not after_tamper["all_valid"],
            }
        )

    artifact = {
        "schema_version": "0.1.0",
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "validation": "prospective-wunderground-freeze-snapshot-contract",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "fixture_scope": {
            "event_id": valid["event_id"],
            "station_code": valid["station_code"],
            "market_date_local": valid["market_date_local"],
            "following_date_local": valid["following_date_local"],
            "target_sha256": valid["target"]["sha256"],
            "trigger_sha256": valid["trigger"]["sha256"],
            "live_evidence": False,
        },
        "case_count": len(cases),
        "passed_case_count": sum(cases.values()),
        "cases": cases,
        "contract_gate_passed": all(cases.values()),
        "interpretation": (
            "Fixture-only storage and replay validation; no collector uptime or live settlement "
            "evidence claim."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
