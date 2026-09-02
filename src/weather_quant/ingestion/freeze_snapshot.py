"""Append-only evidence bundles for prospective Wunderground resolution freezes."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from weather_quant.ingestion.wunderground import parse_daily_page

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _unpadded(value: date) -> str:
    return f"{value.year}-{value.month}-{value.day}"


def _retrieval_record(retrieval: dict[str, Any], parsed: dict[str, Any] | None) -> dict[str, Any]:
    raw = retrieval.get("raw")
    return {
        "url": retrieval.get("url"),
        "requested_at_utc": retrieval.get("requested_at_utc"),
        "received_at_utc": retrieval.get("received_at_utc"),
        "http_status": retrieval.get("http_status"),
        "byte_count": len(raw) if raw is not None else None,
        "sha256": sha256_bytes(raw) if raw is not None else None,
        "parsed": {
            key: parsed.get(key)
            for key in (
                "station_code",
                "station_name",
                "timezone",
                "page_date",
                "daily_high",
                "temperature_unit",
                "observation_count",
                "observation_temperature_count",
                "observation_temperature_max",
            )
        }
        if parsed
        else None,
    }


def build_freeze_snapshot(
    contract: dict[str, Any],
    target_retrieval: dict[str, Any],
    trigger_retrieval: dict[str, Any],
    captured_at_utc: str,
) -> dict[str, Any]:
    """Build a deterministic manifest and fail-closed freeze qualification."""
    target_raw = target_retrieval.get("raw")
    trigger_raw = trigger_retrieval.get("raw")
    target = parse_daily_page(target_raw.decode("utf-8")) if target_raw else None
    trigger = parse_daily_page(trigger_raw.decode("utf-8")) if trigger_raw else None
    market_date = date.fromisoformat(contract["market_date_local"])
    following_date = date.fromordinal(market_date.toordinal() + 1)
    captured = datetime.fromisoformat(captured_at_utc.replace("Z", "+00:00"))
    following_midnight = datetime.combine(
        following_date, time.min, ZoneInfo(contract["timezone"])
    ).astimezone(timezone.utc)
    computed_rule_hash = sha256_bytes(contract["rule_text"].encode("utf-8"))

    checks = {
        "target_http_200_and_raw": target_retrieval.get("http_status") == 200
        and target_raw is not None,
        "trigger_http_200_and_raw": trigger_retrieval.get("http_status") == 200
        and trigger_raw is not None,
        "target_station_match": target is not None
        and target["station_code"] == contract["station_code"],
        "trigger_station_match": trigger is not None
        and trigger["station_code"] == contract["station_code"],
        "target_station_name_match": target is not None
        and target["station_name"] == contract["station_name"],
        "trigger_station_name_match": trigger is not None
        and trigger["station_name"] == contract["station_name"],
        "target_timezone_match": target is not None
        and target["timezone"] == contract["timezone"],
        "trigger_timezone_match": trigger is not None
        and trigger["timezone"] == contract["timezone"],
        "target_date_match": target is not None
        and target["page_date"] == _unpadded(market_date),
        "trigger_date_match": trigger is not None
        and trigger["page_date"] == _unpadded(following_date),
        "target_high_present": target is not None and target["daily_high"] is not None,
        "target_unit_match": target is not None
        and target["temperature_unit"] == contract["temperature_unit"],
        "following_observation_present": trigger is not None
        and trigger["observation_count"] >= 1,
        "captured_after_following_midnight": captured >= following_midnight,
        "rule_hash_valid": SHA256_PATTERN.fullmatch(contract["rule_text_sha256"] or "")
        is not None
        and contract["rule_text_sha256"] == computed_rule_hash,
    }
    core = {
        "schema_version": "0.1.0",
        "event_id": str(contract["event_id"]),
        "market_date_local": market_date.isoformat(),
        "following_date_local": following_date.isoformat(),
        "station_code": contract["station_code"],
        "station_name": contract["station_name"],
        "timezone": contract["timezone"],
        "temperature_unit": contract["temperature_unit"],
        "rule_text_sha256": contract["rule_text_sha256"],
        "rule_version": contract["rule_version"],
        "parser_version": contract["parser_version"],
        "captured_at_utc": captured.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "following_midnight_utc": following_midnight.isoformat().replace("+00:00", "Z"),
        "target": _retrieval_record(target_retrieval, target),
        "trigger": _retrieval_record(trigger_retrieval, trigger),
        "checks": checks,
        "freeze_eligible": all(checks.values()),
        "evidence_class": "PROSPECTIVE_FREEZE_TRIGGER_CAPTURE"
        if all(checks.values())
        else "NOT_FREEZE_ELIGIBLE",
    }
    return {**core, "snapshot_id": sha256_bytes(canonical_json(core))}


def write_freeze_snapshot(
    root: Path,
    manifest: dict[str, Any],
    target_raw: bytes,
    trigger_raw: bytes,
) -> dict[str, Any]:
    """Persist raw bytes and one immutable manifest; identical writes are idempotent."""
    raw_dir = root / "raw" / "sha256"
    manifest_dir = root / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    for content, expected in (
        (target_raw, manifest["target"]["sha256"]),
        (trigger_raw, manifest["trigger"]["sha256"]),
    ):
        if sha256_bytes(content) != expected:
            raise ValueError("raw content does not match manifest checksum")
        path = raw_dir / f"{expected}.html"
        if path.exists():
            if path.read_bytes() != content:
                raise FileExistsError("content-addressed raw path has different bytes")
        else:
            path.write_bytes(content)

    manifest_path = manifest_dir / f"{manifest['snapshot_id']}.json"
    serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists():
        if manifest_path.read_text(encoding="utf-8") != serialized:
            raise FileExistsError("snapshot manifest exists with different content")
        return {"status": "IDEMPOTENT_REPLAY", "manifest_path": str(manifest_path)}
    manifest_path.write_text(serialized, encoding="utf-8")
    return {"status": "APPENDED", "manifest_path": str(manifest_path)}


def verify_freeze_snapshot(root: Path, manifest: dict[str, Any]) -> dict[str, bool]:
    """Verify manifest identity and referenced immutable raw objects."""
    core = {key: value for key, value in manifest.items() if key != "snapshot_id"}
    snapshot_id_valid = sha256_bytes(canonical_json(core)) == manifest["snapshot_id"]
    raw_valid = {}
    for role in ("target", "trigger"):
        digest = manifest[role]["sha256"]
        path = root / "raw" / "sha256" / f"{digest}.html"
        raw_valid[role] = path.exists() and sha256_bytes(path.read_bytes()) == digest
    return {
        "snapshot_id_valid": snapshot_id_valid,
        "target_raw_valid": raw_valid["target"],
        "trigger_raw_valid": raw_valid["trigger"],
        "all_valid": snapshot_id_valid and all(raw_valid.values()),
    }
