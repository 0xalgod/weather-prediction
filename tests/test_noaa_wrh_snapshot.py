from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from weather_quant.ingestion.noaa_wrh_snapshot import (
    WRH_HEADERS,
    build_wrh_snapshot,
    canonical_json,
    verify_wrh_snapshot,
    write_wrh_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "configs/EXP-20260904-kord-prospective-capture.json").read_text())
SOURCE = (ROOT / CONFIG["selection"]["source_artifact"]).read_bytes()


def payload() -> dict:
    rows = [
        {"local_timestamp": f"2026-09-03 {hour:02d}:51", "temperature_f": 70 + hour % 7}
        for hour in range(20)
    ]
    rows.extend(
        [
            {"local_timestamp": "2026-09-04 01:51", "temperature_f": 69},
            {"local_timestamp": "2026-09-04 00:51", "temperature_f": 68},
        ]
    )
    return {
        "station_id": "KORD",
        "station_title": "Chicago, Chicago-O'Hare International Airport",
        "url": "https://www.weather.gov/wrh/timeseries?site=kord&hours=72&units=english_k&hourly=true",
        "observed_at_utc": "2026-09-04T05:55:00Z",
        "headers": list(WRH_HEADERS),
        "rows": rows,
    }


def build(
    selected_payload: dict | None = None,
    captured: str = "2026-09-04T05:55:01Z",
    source: bytes = SOURCE,
) -> dict:
    return build_wrh_snapshot(CONFIG, selected_payload or payload(), source, captured)


def test_valid_fixture_qualifies_and_selects_minimum_following_timestamp() -> None:
    manifest = build()
    assert manifest["capture_eligible"] is True
    assert manifest["target_row_count"] == 20
    assert manifest["following_row_count"] == 2
    assert manifest["first_following_row"]["local_timestamp"] == "2026-09-04 00:51"
    assert manifest["following_midnight_utc"] == "2026-09-04T05:00:00Z"
    assert all(manifest["checks"].values())


@pytest.mark.parametrize(
    ("mutation", "failed_check"),
    [
        (lambda value: value.update(station_id="KAAA"), "station_identity_match"),
        (lambda value: value["headers"].__setitem__(1, "Temp. (°C)"), "schema_match"),
        (lambda value: value.update(url="https://example.test"), "source_url_match"),
        (lambda value: value.update(rows=value["rows"][:19]), "target_coverage"),
        (
            lambda value: value.update(
                rows=[
                    row
                    for row in value["rows"]
                    if not row["local_timestamp"].startswith("2026-09-04")
                ]
            ),
            "following_observation_present",
        ),
        (
            lambda value: value["rows"].append(copy.deepcopy(value["rows"][0])),
            "duplicate_timestamps",
        ),
        (lambda value: value["rows"][0].update(temperature_f="bad"), "row_parse_valid"),
    ],
)
def test_payload_contract_failures_are_closed(mutation, failed_check) -> None:
    selected = payload()
    mutation(selected)
    manifest = build(selected)
    assert manifest["capture_eligible"] is False
    assert manifest["checks"][failed_check] is False
    assert manifest["evidence_class"] == "NOT_FREEZE_ELIGIBLE"


def test_pre_midnight_capture_fails_closed() -> None:
    manifest = build(captured="2026-09-04T04:59:59Z")
    assert manifest["checks"]["captured_after_following_midnight"] is False
    assert manifest["capture_eligible"] is False


def test_source_checksum_tamper_fails_closed() -> None:
    manifest = build(source=SOURCE + b" ")
    assert manifest["checks"]["source_artifact_checksum_match"] is False
    assert manifest["capture_eligible"] is False


def test_write_replay_revision_and_tamper_detection(tmp_path) -> None:
    selected = payload()
    manifest = build(selected)
    assert write_wrh_snapshot(tmp_path, manifest, selected)["status"] == "APPENDED"
    assert write_wrh_snapshot(tmp_path, manifest, selected)["status"] == "IDEMPOTENT_REPLAY"

    changed = payload()
    changed["rows"][0]["temperature_f"] = 71
    revision = build(changed, captured="2026-09-04T05:56:01Z")
    assert write_wrh_snapshot(tmp_path, revision, changed)["status"] == "APPENDED"
    assert len(list((tmp_path / "manifests").glob("*.json"))) == 2

    raw_path = tmp_path / "raw" / "sha256" / f"{manifest['payload_sha256']}.json"
    raw_path.write_bytes(b"tampered")
    assert verify_wrh_snapshot(tmp_path, manifest)["all_valid"] is False


def test_writer_rejects_payload_not_matching_manifest(tmp_path) -> None:
    selected = payload()
    manifest = build(selected)
    changed = copy.deepcopy(selected)
    changed["rows"][0]["temperature_f"] = 99
    with pytest.raises(ValueError, match="payload does not match"):
        write_wrh_snapshot(tmp_path, manifest, changed)


def test_manifest_is_deterministic() -> None:
    assert canonical_json(build()) == canonical_json(build())
