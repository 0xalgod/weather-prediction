"""Fail-closed manifests for sanitized NOAA WRH rendered-table captures."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

WRH_HEADERS = (
    "Date/Time (L)",
    "Temp. (°F)",
    "Dew Point (°F)",
    "Relative Humidity (%)",
    "Heat Index (°F)",
    "Wind Direction",
    "Wind Speed (kts)",
    "Visibility (miles)",
    "Weather",
    "Clouds (x100 ft)",
    "Sea Level Pressure (mb)",
    "Station Pressure (in Hg)",
    "Altimeter Setting (in Hg)",
    "1 Hour Precip (in)",
    "3 Hour Precip (in)",
    "6 Hour Precip (in)",
    "24 Hour Precip (in)",
    "6 Hr Max (°F)",
    "6 Hr Min (°F)",
    "24 Hr Max (°F)",
    "24 Hr Min (°F)",
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _local_timestamp(value: str, timezone_name: str) -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=ZoneInfo(timezone_name))


def _locked_event(source: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    matches = [
        row
        for row in source.get("chicago_audits", [])
        if str(row.get("event_id")) == event_id
    ]
    return matches[0] if len(matches) == 1 else None


def build_wrh_snapshot(
    contract: dict[str, Any],
    payload: dict[str, Any],
    source_artifact_bytes: bytes,
    captured_at_utc: str,
) -> dict[str, Any]:
    """Validate one sanitized DOM payload and build a deterministic manifest."""
    selection = contract["selection"]
    observation = contract["observation_contract"]
    acceptance = contract["acceptance"]
    captured = _utc(captured_at_utc)
    timezone_name = observation["timezone"]
    following_date = observation["following_local_date"]
    following_midnight = datetime.combine(
        datetime.fromisoformat(following_date).date(), time.min, ZoneInfo(timezone_name)
    )

    source_checksum = sha256_bytes(source_artifact_bytes)
    try:
        source = json.loads(source_artifact_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        source = {}
    event_id = str(selection["event_id"])
    locked_event = _locked_event(source, event_id)
    identities = locked_event.get("token_identities", []) if locked_event else []

    rows = payload.get("rows", []) if isinstance(payload.get("rows"), list) else []
    parsed_rows: list[tuple[dict[str, Any], datetime]] = []
    row_parse_valid = True
    for row in rows:
        try:
            temperature = float(row["temperature_f"])
            local_time = _local_timestamp(row["local_timestamp"], timezone_name)
            parsed_rows.append(({**row, "temperature_f": temperature}, local_time))
        except (KeyError, TypeError, ValueError):
            row_parse_valid = False

    timestamps = [row[0]["local_timestamp"] for row in parsed_rows]
    target_rows = [
        row
        for row, stamp in parsed_rows
        if stamp.date().isoformat() == observation["target_local_date"]
    ]
    following_rows = [
        (row, stamp)
        for row, stamp in parsed_rows
        if stamp.date().isoformat() == following_date
    ]
    first_following = min(following_rows, key=lambda item: item[1])[0] if following_rows else None
    identity_counts_valid = (
        len(identities) == selection["market_count"]
        and len({row.get("condition_id") for row in identities}) == selection["condition_count"]
        and sum(len(row.get("token_ids", [])) for row in identities) == selection["token_count"]
    )

    checks = {
        "captured_after_following_midnight": captured
        >= following_midnight.astimezone(timezone.utc),
        "station_identity_match": payload.get("station_id") == observation["station_id"]
        and payload.get("station_title") == observation["rendered_station_title"],
        "source_url_match": payload.get("url") == observation["declared_url"],
        "schema_match": tuple(payload.get("headers", [])) == WRH_HEADERS,
        "row_parse_valid": row_parse_valid and len(parsed_rows) == len(rows),
        "target_coverage": len(target_rows)
        >= acceptance["target_date_timestamped_numeric_rows_minimum"],
        "following_observation_present": len(following_rows)
        >= acceptance["following_date_timestamped_numeric_rows_minimum"],
        "duplicate_timestamps": len(timestamps) == len(set(timestamps)),
        "source_artifact_checksum_match": source_checksum
        == selection["source_artifact_sha256"],
        "locked_event_match": locked_event is not None
        and locked_event.get("rule_text_sha256") == selection["rule_text_sha256"],
        "locked_identity_counts_match": identity_counts_valid,
    }
    sanitized_payload = {
        "station_id": payload.get("station_id"),
        "station_title": payload.get("station_title"),
        "url": payload.get("url"),
        "observed_at_utc": payload.get("observed_at_utc"),
        "headers": payload.get("headers"),
        "rows": rows,
    }
    payload_sha256 = sha256_bytes(canonical_json(sanitized_payload))
    eligible = all(checks.values())
    core = {
        "schema_version": "1.0.0",
        "run_id": contract["run_id"],
        "event_id": event_id,
        "rule_text_sha256": selection["rule_text_sha256"],
        "source_artifact_sha256": source_checksum,
        "captured_at_utc": captured.isoformat().replace("+00:00", "Z"),
        "following_midnight_utc": following_midnight.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "payload_sha256": payload_sha256,
        "row_count": len(rows),
        "target_row_count": len(target_rows),
        "following_row_count": len(following_rows),
        "first_following_row": first_following,
        "checks": checks,
        "capture_eligible": eligible,
        "evidence_class": (
            "PROSPECTIVE_TRIGGER_CAPTURE_PASS_PENDING_SETTLEMENT"
            if eligible
            else "NOT_FREEZE_ELIGIBLE"
        ),
    }
    return {**core, "snapshot_id": sha256_bytes(canonical_json(core))}


def write_wrh_snapshot(
    root: Path, manifest: dict[str, Any], payload: dict[str, Any]
) -> dict[str, str]:
    """Append one content-addressed sanitized payload and immutable manifest."""
    payload_bytes = canonical_json(payload)
    if sha256_bytes(payload_bytes) != manifest["payload_sha256"]:
        raise ValueError("payload does not match manifest checksum")
    payload_dir = root / "raw" / "sha256"
    manifest_dir = root / "manifests"
    payload_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    payload_path = payload_dir / f"{manifest['payload_sha256']}.json"
    if payload_path.exists() and payload_path.read_bytes() != payload_bytes:
        raise FileExistsError("content-addressed payload path has different bytes")
    if not payload_path.exists():
        payload_path.write_bytes(payload_bytes)
    manifest_path = manifest_dir / f"{manifest['snapshot_id']}.json"
    serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists():
        if manifest_path.read_text() != serialized:
            raise FileExistsError("snapshot manifest exists with different content")
        return {"status": "IDEMPOTENT_REPLAY", "manifest_path": str(manifest_path)}
    manifest_path.write_text(serialized)
    return {"status": "APPENDED", "manifest_path": str(manifest_path)}


def verify_wrh_snapshot(
    root: Path, manifest: dict[str, Any]
) -> dict[str, bool]:
    """Verify manifest identity and its content-addressed sanitized payload."""
    core = {key: value for key, value in manifest.items() if key != "snapshot_id"}
    snapshot_valid = sha256_bytes(canonical_json(core)) == manifest["snapshot_id"]
    payload_path = root / "raw" / "sha256" / f"{manifest['payload_sha256']}.json"
    payload_valid = payload_path.exists() and sha256_bytes(payload_path.read_bytes()) == manifest[
        "payload_sha256"
    ]
    return {
        "snapshot_id_valid": snapshot_valid,
        "payload_valid": payload_valid,
        "all_valid": snapshot_valid and payload_valid,
    }
