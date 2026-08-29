"""Deterministic anomaly cohorts and audit samples for closed Gamma events."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from weather_quant.ingestion.polymarket_markets import DiscoveryError, parse_json_array


JsonObject = Dict[str, Any]

COHORTS = (
    "NO_EVENT_RESOLUTION_SOURCE",
    "EVENT_NOT_AUTOMATICALLY_RESOLVED",
    "EVENT_MISSING_CLOSED_TIME",
    "MARKET_IDENTIFIER_INCOMPLETE",
    "MARKET_NOT_UMA_RESOLVED",
)


def iter_raw_events(raw_directory: Path) -> Iterable[Tuple[Mapping[str, Any], str]]:
    """Yield events from immutable envelopes in stable filename order."""

    paths = sorted(raw_directory.glob("page-*.json"))
    if not paths:
        raise FileNotFoundError(f"no raw page envelopes found in {raw_directory}")
    for path in paths:
        with path.open("r", encoding="utf-8") as source:
            envelope = json.load(source)
        payload = envelope.get("payload")
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise DiscoveryError(f"invalid event envelope: {path}")
        checksum = str(envelope.get("content_sha256") or "")
        if not checksum:
            raise DiscoveryError(f"envelope lacks content checksum: {path}")
        for event in payload["events"]:
            if not isinstance(event, dict):
                raise DiscoveryError(f"non-object event in {path}")
            yield event, checksum


def classify_closed_event(event: Mapping[str, Any], page_checksum: str) -> JsonObject:
    """Classify one closed event without silently discarding malformed markets."""

    event_id = str(event.get("id") or "")
    if not event_id:
        raise DiscoveryError("closed audit event id is required")
    markets = event.get("markets")
    if not isinstance(markets, list):
        raise DiscoveryError(f"event {event_id} markets must be an array")

    cohorts: List[str] = []
    if not event.get("resolutionSource"):
        cohorts.append("NO_EVENT_RESOLUTION_SOURCE")
    if event.get("automaticallyResolved") is not True:
        cohorts.append("EVENT_NOT_AUTOMATICALLY_RESOLVED")
    if not event.get("closedTime"):
        cohorts.append("EVENT_MISSING_CLOSED_TIME")

    anomalous_markets: List[JsonObject] = []
    market_summaries: List[JsonObject] = []
    for market in markets:
        if not isinstance(market, dict):
            raise DiscoveryError(f"event {event_id} contains a non-object market")
        reasons: List[str] = []
        try:
            outcomes = parse_json_array(market.get("outcomes"), "outcomes")
            token_ids = parse_json_array(market.get("clobTokenIds"), "clobTokenIds")
            prices = parse_json_array(market.get("outcomePrices"), "outcomePrices")
        except DiscoveryError:
            outcomes, token_ids, prices = [], [], []
            reasons.append("MARKET_IDENTIFIER_INCOMPLETE")
        if (
            not market.get("id")
            or not market.get("conditionId")
            or len(outcomes) != 2
            or len(token_ids) != 2
        ):
            reasons.append("MARKET_IDENTIFIER_INCOMPLETE")
        if market.get("umaResolutionStatus") != "resolved":
            reasons.append("MARKET_NOT_UMA_RESOLVED")
        reasons = sorted(set(reasons))
        cohorts.extend(reasons)
        summary = {
            "market_id": str(market.get("id") or "") or None,
            "condition_id": market.get("conditionId"),
            "bucket_label": market.get("groupItemTitle"),
            "outcomes": outcomes,
            "token_ids": [str(value) for value in token_ids],
            "outcome_prices": prices,
            "uma_resolution_status": market.get("umaResolutionStatus"),
        }
        market_summaries.append(summary)
        if reasons:
            anomalous_markets.append({**summary, "reason_codes": reasons})

    unique_cohorts = sorted(set(cohorts))
    return {
        "event_id": event_id,
        "title": event.get("title"),
        "slug": event.get("slug"),
        "end_date": event.get("endDate"),
        "closed_time": event.get("closedTime"),
        "resolution_source": event.get("resolutionSource"),
        "automatically_resolved": event.get("automaticallyResolved"),
        "page_content_sha256": page_checksum,
        "cohorts": unique_cohorts,
        "market_count": len(markets),
        "anomalous_markets": anomalous_markets,
        "markets": market_summaries,
    }


def _rank(seed: str, event_id: str) -> str:
    return hashlib.sha256(f"{seed}|{event_id}".encode("utf-8")).hexdigest()


def select_stratified_sample(
    records: Sequence[JsonObject],
    sample_size: int = 20,
    anomaly_per_cohort: int = 3,
    clean_target: int = 5,
    seed: str = "EXP-20260830-phase1-manual-reconciliation-v1",
) -> Tuple[List[JsonObject], JsonObject]:
    """Select unique events across anomaly cohorts, then clean/hash-fill."""

    if sample_size < 1 or anomaly_per_cohort < 0 or clean_target < 0:
        raise ValueError("sample parameters must be non-negative and sample_size positive")
    ordered = sorted(records, key=lambda item: (_rank(seed, item["event_id"]), item["event_id"]))
    selected: List[JsonObject] = []
    selected_ids = set()
    achieved = Counter()

    def add_candidates(candidates: Iterable[JsonObject], limit: int, stratum: str) -> None:
        for record in candidates:
            if achieved[stratum] >= limit or len(selected) >= sample_size:
                return
            if record["event_id"] in selected_ids:
                continue
            selected.append({**record, "selection_stratum": stratum})
            selected_ids.add(record["event_id"])
            achieved[stratum] += 1

    for cohort in COHORTS:
        add_candidates((item for item in ordered if cohort in item["cohorts"]), anomaly_per_cohort, cohort)
    add_candidates((item for item in ordered if not item["cohorts"]), clean_target, "CLEAN")
    add_candidates((item for item in ordered if item["event_id"] not in selected_ids), sample_size, "HASH_FILL")

    if len(selected) != sample_size:
        raise DiscoveryError(f"requested {sample_size} sample events but selected {len(selected)}")
    metadata = {
        "seed": seed,
        "sample_size": sample_size,
        "anomaly_per_cohort_target": anomaly_per_cohort,
        "clean_target": clean_target,
        "selection_stratum_counts": dict(sorted(Counter(x["selection_stratum"] for x in selected).items())),
        "sample_cohort_coverage": {
            cohort: sum(cohort in item["cohorts"] for item in selected) for cohort in COHORTS
        },
    }
    return selected, metadata


def build_closed_audit(records: Sequence[JsonObject]) -> JsonObject:
    """Build overlap-aware cohort counts for all classified events."""

    event_counts = {cohort: sum(cohort in item["cohorts"] for item in records) for cohort in COHORTS}
    intersection_counts = Counter(
        "+".join(item["cohorts"]) if item["cohorts"] else "CLEAN" for item in records
    )
    market_counts = Counter(
        reason
        for item in records
        for market in item["anomalous_markets"]
        for reason in market["reason_codes"]
    )
    return {
        "event_count": len(records),
        "clean_event_count": sum(not item["cohorts"] for item in records),
        "anomalous_event_count": sum(bool(item["cohorts"]) for item in records),
        "cohort_event_counts": event_counts,
        "cohort_market_counts": {
            cohort: market_counts[cohort]
            for cohort in ("MARKET_IDENTIFIER_INCOMPLETE", "MARKET_NOT_UMA_RESOLVED")
        },
        "cohort_intersection_counts": dict(sorted(intersection_counts.items())),
    }
