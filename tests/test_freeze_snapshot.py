from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from weather_quant.ingestion.freeze_snapshot import (
    build_freeze_snapshot,
    verify_freeze_snapshot,
    write_freeze_snapshot,
)

FIXTURES = Path(__file__).parent / "fixtures"
RULE_TEXT = "Synthetic KORD next-day-first-datapoint freeze rule."


def contract() -> dict:
    return {
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


def retrieval(name: str, raw: bytes) -> dict:
    return {
        "url": f"https://example.test/{name}",
        "requested_at_utc": "2026-09-02T05:05:00Z",
        "received_at_utc": "2026-09-02T05:05:01Z",
        "http_status": 200,
        "raw": raw,
    }


def raw_pages() -> tuple[bytes, bytes]:
    return (
        (FIXTURES / "wunderground_kord_target.html").read_bytes(),
        (FIXTURES / "wunderground_kord_trigger.html").read_bytes(),
    )


def build(captured_at: str = "2026-09-02T05:05:02Z", override: dict | None = None) -> dict:
    target, trigger = raw_pages()
    selected = contract()
    selected.update(override or {})
    return build_freeze_snapshot(
        selected, retrieval("target", target), retrieval("trigger", trigger), captured_at
    )


def test_valid_bundle_qualifies_after_chicago_midnight() -> None:
    manifest = build()
    assert manifest["freeze_eligible"] is True
    assert manifest["following_midnight_utc"] == "2026-09-02T05:00:00Z"
    assert all(manifest["checks"].values())


@pytest.mark.parametrize(
    ("captured_at", "override", "failed_check"),
    [
        ("2026-09-02T04:59:59Z", {}, "captured_after_following_midnight"),
        ("2026-09-02T05:05:02Z", {"station_code": "KAAA"}, "target_station_match"),
        ("2026-09-02T05:05:02Z", {"temperature_unit": "C"}, "target_unit_match"),
        ("2026-09-02T05:05:02Z", {"rule_text_sha256": "0" * 64}, "rule_hash_valid"),
    ],
)
def test_contract_mismatches_fail_closed(captured_at, override, failed_check) -> None:
    manifest = build(captured_at, override)
    assert manifest["freeze_eligible"] is False
    assert manifest["evidence_class"] == "NOT_FREEZE_ELIGIBLE"
    assert manifest["checks"][failed_check] is False


def test_empty_trigger_observations_fail_closed() -> None:
    target, trigger = raw_pages()
    trigger = trigger.replace(b'[{"ts":1788325200,"temp":70}]', b"[]")
    manifest = build_freeze_snapshot(
        contract(),
        retrieval("target", target),
        retrieval("trigger", trigger),
        "2026-09-02T05:05:02Z",
    )
    assert manifest["checks"]["following_observation_present"] is False
    assert manifest["freeze_eligible"] is False


def test_write_is_idempotent_changed_content_appends_and_tamper_fails(tmp_path) -> None:
    target, trigger = raw_pages()
    first = build()
    assert write_freeze_snapshot(tmp_path, first, target, trigger)["status"] == "APPENDED"
    assert write_freeze_snapshot(tmp_path, first, target, trigger)["status"] == "IDEMPOTENT_REPLAY"
    assert len(list((tmp_path / "manifests").glob("*.json"))) == 1

    changed_target = target.replace("82°F".encode(), "83°F".encode()).replace(
        b'"temp":82', b'"temp":83'
    )
    changed = build_freeze_snapshot(
        contract(),
        retrieval("target", changed_target),
        retrieval("trigger", trigger),
        "2026-09-02T05:06:02Z",
    )
    assert write_freeze_snapshot(tmp_path, changed, changed_target, trigger)["status"] == "APPENDED"
    assert len(list((tmp_path / "manifests").glob("*.json"))) == 2

    target_path = tmp_path / "raw" / "sha256" / f"{first['target']['sha256']}.html"
    target_path.write_bytes(b"tampered")
    assert verify_freeze_snapshot(tmp_path, first)["all_valid"] is False
