"""Settlement/current-page comparison helpers."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

from weather_quant.normalization.manual_reconciliation import outcome_rule_check

CITY_PATTERN = re.compile(r"^Highest temperature in (.+?) on ")


def city_from_title(title: str) -> str:
    match = CITY_PATTERN.match(title)
    if not match:
        raise ValueError(f"unparseable weather title: {title}")
    return match.group(1)


def classify_settlement_record(record: Mapping[str, Any]) -> dict[str, Any]:
    eligible = (
        record.get("identity_match") is True
        and record.get("terminal_status") == "EXACT_TERMINAL_WINNER"
        and record.get("observed_high_display") is not None
    )
    base = {
        "event_id": str(record["event_id"]),
        "city": city_from_title(str(record["title"])),
        "title": record["title"],
        "station_code": record.get("rule", {}).get("station_code"),
        "terminal_winner_bucket": record.get("terminal_winner_bucket"),
        "observed_high_display": record.get("observed_high_display"),
        "eligible": eligible,
    }
    if not eligible:
        return {
            **base,
            "comparison": "INELIGIBLE",
            "disposition": record.get("disposition"),
            "training_eligible": False,
        }
    comparison = outcome_rule_check(
        record.get("terminal_winner_bucket"), record.get("observed_high_display")
    )
    if comparison == "MATCH":
        disposition = "CURRENT_PAGE_TERMINAL_BUCKET_MATCH"
        training_eligible = True
    elif comparison == "MISMATCH":
        disposition = "HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT"
        training_eligible = False
    else:
        disposition = "UNRESOLVED_ELIGIBLE"
        training_eligible = False
    return {
        **base,
        "comparison": comparison,
        "disposition": disposition,
        "training_eligible": training_eligible,
    }


def wilson_interval(
    successes: int, trials: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    if trials <= 0 or successes < 0 or successes > trials:
        raise ValueError("invalid binomial counts")
    proportion = successes / trials
    denominator = 1 + z**2 / trials
    centre = (proportion + z**2 / (2 * trials)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / trials + z**2 / (4 * trials**2)
        )
        / denominator
    )
    return centre - margin, centre + margin
