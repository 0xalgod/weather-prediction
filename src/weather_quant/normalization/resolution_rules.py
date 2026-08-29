"""Validation contract for versioned maximum-temperature resolution records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


RECONCILED = "RECONCILED"
CANDIDATE_STATION_UNVERIFIED = "CANDIDATE_STATION_UNVERIFIED"
_BUCKET_LABEL = re.compile(
    r"^(?P<lower>-?\d+)(?:-(?P<upper>-?\d+))?°(?P<unit>[CF])(?: or (?P<tail>below|higher))?$"
)


class ResolutionRegistryError(ValueError):
    """Raised when a registry record is unsafe for research use."""


def rule_sha256(rule_text: str) -> str:
    """Hash exact rule text so revisions create new registry versions."""

    return hashlib.sha256(rule_text.encode("utf-8")).hexdigest()


def parse_bucket_bounds(label: str, expected_unit: str) -> Dict[str, Any]:
    """Convert a Polymarket discrete temperature label to numeric bounds."""

    match = _BUCKET_LABEL.fullmatch(label.strip())
    if match is None:
        raise ResolutionRegistryError(f"unparseable bucket label: {label}")
    if match.group("unit") != expected_unit:
        raise ResolutionRegistryError("bucket unit disagrees with resolution rule")
    lower = int(match.group("lower"))
    upper = int(match.group("upper") or match.group("lower"))
    tail = match.group("tail")
    return {
        "lower_bound": None if tail == "below" else lower,
        "upper_bound": None if tail == "higher" else upper,
        "lower_inclusive": True,
        "upper_inclusive": True,
    }


def build_bucket_records(markets: Sequence[Mapping[str, Any]], unit: str) -> List[Dict[str, Any]]:
    """Build registry buckets, rejecting incomplete market/token identity."""

    records = []
    for market in markets:
        tokens = market.get("clobTokenIds")
        if isinstance(tokens, str):
            tokens = json.loads(tokens)
        if not market.get("id") or not market.get("conditionId") or not isinstance(tokens, list) or len(tokens) != 2:
            raise ResolutionRegistryError("cannot build bucket with incomplete identifiers")
        label = str(market.get("groupItemTitle") or "")
        records.append({
            "market_id": str(market["id"]),
            "condition_id": str(market["conditionId"]),
            "yes_token_id": str(tokens[0]),
            "no_token_id": str(tokens[1]),
            "label": label,
            **parse_bucket_bounds(label, unit),
        })
    return records


def validate_bucket_partition(buckets: Sequence[Mapping[str, Any]], precision: float) -> None:
    """Require one exhaustive, non-overlapping inclusive discrete partition."""

    if not buckets:
        raise ResolutionRegistryError("reconciled record requires buckets")
    ordered = sorted(buckets, key=lambda item: float("-inf") if item["lower_bound"] is None else item["lower_bound"])
    if ordered[0]["lower_bound"] is not None or ordered[-1]["upper_bound"] is not None:
        raise ResolutionRegistryError("bucket partition must have open lower and upper tails")
    if sum(item["lower_bound"] is None for item in ordered) != 1 or sum(item["upper_bound"] is None for item in ordered) != 1:
        raise ResolutionRegistryError("bucket partition must have exactly one tail on each side")
    for item in ordered:
        if item.get("lower_inclusive") is not True or item.get("upper_inclusive") is not True:
            raise ResolutionRegistryError("temperature buckets use inclusive discrete bounds")
        if not all(item.get(field) for field in ("market_id", "condition_id", "yes_token_id", "no_token_id", "label")):
            raise ResolutionRegistryError("bucket identifier fields are required")
    for left, right in zip(ordered, ordered[1:]):
        if left["upper_bound"] is None or right["lower_bound"] is None:
            raise ResolutionRegistryError("tail bucket is in an invalid position")
        expected = float(left["upper_bound"]) + precision
        if abs(float(right["lower_bound"]) - expected) > 1e-9:
            raise ResolutionRegistryError("bucket partition contains a gap or overlap")


def validate_resolution_record(record: Mapping[str, Any]) -> List[str]:
    """Validate critical semantics and return non-trading exclusion reasons."""

    required = {"schema_version", "registry_record_id", "event_id", "event_slug", "city_label", "market_date_local", "disposition", "exclusion_reasons", "rule", "buckets", "provenance"}
    missing = sorted(required - record.keys())
    if missing:
        raise ResolutionRegistryError(f"missing top-level fields: {missing}")
    date.fromisoformat(str(record["market_date_local"]))
    disposition = record["disposition"]
    exclusions = list(record["exclusion_reasons"])
    if disposition not in (RECONCILED, CANDIDATE_STATION_UNVERIFIED):
        if not exclusions:
            raise ResolutionRegistryError("NO_TRADE record requires an exclusion reason")
        return exclusions
    if disposition == RECONCILED and exclusions:
        raise ResolutionRegistryError("reconciled record cannot contain exclusion reasons")
    if disposition == CANDIDATE_STATION_UNVERIFIED and exclusions != ["STATION_TIMEZONE_UNVERIFIED"]:
        raise ResolutionRegistryError("station candidate requires its exact unverified reason")

    rule = record["rule"]
    critical = ("provider", "source_url", "station_code", "station_name", "timezone", "temperature_unit", "temperature_precision", "rounding_mode", "observation_window", "rule_text", "rule_text_sha256", "rule_version")
    absent = [field for field in critical if rule.get(field) in (None, "")]
    if absent:
        raise ResolutionRegistryError(f"reconciled rule missing critical fields: {absent}")
    if rule["temperature_unit"] not in ("C", "F"):
        raise ResolutionRegistryError("temperature unit must be C or F")
    try:
        ZoneInfo(rule["timezone"])
    except ZoneInfoNotFoundError as error:
        raise ResolutionRegistryError("timezone must be a valid IANA zone") from error
    if rule_sha256(rule["rule_text"]) != rule["rule_text_sha256"]:
        raise ResolutionRegistryError("rule hash does not match exact rule text")
    window = rule["observation_window"]
    if window != {"basis": "LOCAL_CALENDAR_DAY", "start_local": "00:00:00", "end_local": "23:59:59.999999", "end_inclusive": True}:
        raise ResolutionRegistryError("observation window is not an explicit local calendar day")
    precision = float(rule["temperature_precision"])
    if precision <= 0:
        raise ResolutionRegistryError("temperature precision must be positive")
    validate_bucket_partition(record["buckets"], precision)

    provenance = record["provenance"]
    for field in ("gamma_observed_at_utc", "resolution_observed_at_utc"):
        parsed = datetime.fromisoformat(str(provenance[field]).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ResolutionRegistryError(f"{field} must include timezone")
    if disposition == RECONCILED:
        evidence_fields = ("station_metadata_source_url", "station_metadata_sha256", "timezone_boundary_version", "timezone_boundary_sha256", "timezone_names_sha256")
        absent_evidence = [field for field in evidence_fields if provenance.get(field) in (None, "")]
        if absent_evidence:
            raise ResolutionRegistryError(f"reconciled record missing station evidence: {absent_evidence}")
    return exclusions
