"""Rules used to reconcile sampled Gamma events with their resolution pages."""

from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse


JsonObject = Dict[str, Any]
_RULE_RE = re.compile(
    r"highest temperature recorded at the (?P<station_name>.+?) in degrees "
    r"(?P<unit>Fahrenheit|Celsius) on (?P<date>\d{1,2} [A-Z][a-z]+ '\d{2})\."
)
_HIGH_RE = re.compile(r"Day High &(?:amp;)? Low.*?High\s+(?P<value>-?\d+)°(?P<unit>[CF])", re.S)
_BUCKET_RE = re.compile(r"^(?P<low>-?\d+)(?:-(?P<high>-?\d+))?°(?P<unit>[CF])(?: or (?P<tail>below|higher))?$")


def parse_resolution_rule(description: str, source_url: Optional[str]) -> JsonObject:
    """Extract the explicit station name, station code, unit and rule date."""

    match = _RULE_RE.search(description or "")
    station_code = None
    if source_url:
        station_code = urlparse(source_url).path.rstrip("/").split("/")[-1] or None
    return {
        "station_name": match.group("station_name") if match else None,
        "station_code": station_code,
        "unit": {"Fahrenheit": "F", "Celsius": "C"}.get(match.group("unit")) if match else None,
        "rule_date": match.group("date") if match else None,
        "rule_parse_complete": bool(match and station_code),
    }


def parse_wunderground_high(page: str) -> Optional[JsonObject]:
    """Read the displayed finalized daily high from a Wunderground HTML page."""

    visible = html.unescape(re.sub(r"<[^>]+>", " ", page))
    visible = re.sub(r"\s+", " ", visible)
    match = _HIGH_RE.search(visible)
    if not match:
        return None
    return {"value": int(match.group("value")), "unit": match.group("unit")}


def terminal_winner(markets: Sequence[Mapping[str, Any]]) -> Tuple[Optional[str], str]:
    """Return the sole exact Yes=1 winner, or an explicit non-terminal reason."""

    winners = []
    for market in markets:
        prices = market.get("outcomePrices")
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except json.JSONDecodeError:
                return None, "INVALID_OUTCOME_PRICES"
        if prices == ["1", "0"] or prices == [1, 0]:
            winners.append(str(market.get("groupItemTitle") or ""))
    if len(winners) == 1:
        return winners[0], "EXACT_TERMINAL_WINNER"
    if not winners:
        return None, "NO_EXACT_TERMINAL_WINNER"
    return None, "MULTIPLE_EXACT_TERMINAL_WINNERS"


def identity_matches(sample_markets: Sequence[Mapping[str, Any]], live_markets: Sequence[Mapping[str, Any]]) -> bool:
    """Compare market, condition and token identity independent of source ordering."""

    def identities(markets: Sequence[Mapping[str, Any]]) -> set:
        output = set()
        for market in markets:
            tokens = market.get("clobTokenIds", market.get("token_ids", []))
            if isinstance(tokens, str):
                tokens = json.loads(tokens)
            output.add((str(market.get("id", market.get("market_id")) or ""), str(market.get("conditionId", market.get("condition_id")) or ""), tuple(str(x) for x in tokens)))
        return output
    return identities(sample_markets) == identities(live_markets)


def outcome_rule_check(bucket: Optional[str], observed: Optional[Mapping[str, Any]]) -> str:
    """Check whether a displayed daily high unambiguously belongs to the winner bucket."""

    if not bucket or not observed:
        return "INCONCLUSIVE"
    match = _BUCKET_RE.match(bucket)
    if not match:
        return "UNPARSEABLE_BUCKET"
    value = float(observed["value"])
    observed_unit = observed["unit"]
    bucket_unit = match.group("unit")
    # A displayed whole degree represents a rounding interval. Preserve it when converting units.
    observed_low, observed_high = value - 0.5, value + 0.5
    if observed_unit == "C" and bucket_unit == "F":
        observed_low, observed_high = observed_low * 9 / 5 + 32, observed_high * 9 / 5 + 32
    elif observed_unit == "F" and bucket_unit == "C":
        observed_low, observed_high = (observed_low - 32) * 5 / 9, (observed_high - 32) * 5 / 9
    elif observed_unit != bucket_unit:
        return "INCONCLUSIVE_UNIT"

    low = float(match.group("low"))
    high = float(match.group("high") or match.group("low"))
    tail = match.group("tail")
    if tail == "below":
        inside = observed_high <= high + 0.5
        outside = observed_low >= high + 0.5
    elif tail == "higher":
        inside = observed_low >= low - 0.5
        outside = observed_high <= low - 0.5
    else:
        inside = observed_low >= low - 0.5 and observed_high <= high + 0.5
        outside = observed_high <= low - 0.5 or observed_low >= high + 0.5
    return "MATCH" if inside else "MISMATCH" if outside else "AMBIGUOUS_ROUNDING"
