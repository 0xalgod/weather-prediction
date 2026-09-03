"""Transparent probability and executable-price primitives for the MVP slice."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from weather_quant.normalization.resolution_rules import validate_bucket_partition


def normal_cdf(value: float, mean: float, standard_deviation: float) -> float:
    """Return a Gaussian CDF without adding a scientific-computing dependency."""
    if not math.isfinite(mean) or not math.isfinite(standard_deviation):
        raise ValueError("mean and standard deviation must be finite")
    if standard_deviation <= 0:
        raise ValueError("standard deviation must be positive")
    z_score = (value - mean) / (standard_deviation * math.sqrt(2.0))
    return 0.5 * (1.0 + math.erf(z_score))


def bucket_probability(
    lower_bound: int | None,
    upper_bound: int | None,
    mean_f: float,
    standard_deviation_f: float,
    continuity_correction_f: float = 0.5,
) -> float:
    """Map one inclusive integer bucket to Gaussian probability mass."""
    if lower_bound is None and upper_bound is None:
        raise ValueError("bucket cannot be unbounded on both sides")
    if continuity_correction_f <= 0:
        raise ValueError("continuity correction must be positive")
    lower_cdf = (
        0.0
        if lower_bound is None
        else normal_cdf(
            lower_bound - continuity_correction_f,
            mean_f,
            standard_deviation_f,
        )
    )
    upper_cdf = (
        1.0
        if upper_bound is None
        else normal_cdf(
            upper_bound + continuity_correction_f,
            mean_f,
            standard_deviation_f,
        )
    )
    probability = upper_cdf - lower_cdf
    if probability < 0 or probability > 1:
        raise ValueError("bucket probability outside [0, 1]")
    return probability


def gaussian_bucket_probabilities(
    buckets: Sequence[Mapping[str, Any]],
    mean_f: float,
    standard_deviation_f: float,
    precision_f: float = 1.0,
) -> list[dict[str, Any]]:
    """Validate an exhaustive partition and attach baseline probabilities."""
    validate_bucket_partition(buckets, precision_f)
    output = []
    for bucket in buckets:
        probability = bucket_probability(
            bucket["lower_bound"],
            bucket["upper_bound"],
            mean_f,
            standard_deviation_f,
            continuity_correction_f=precision_f / 2,
        )
        output.append({**bucket, "model_probability": probability})
    total = math.fsum(row["model_probability"] for row in output)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"bucket probabilities do not sum to one: {total}")
    return output


def quantile_cdf_anchors(
    p10_f: float,
    p25_f: float,
    p50_f: float,
    p75_f: float,
    p90_f: float,
    minimum_tail_width_f: float = 1.0,
) -> list[tuple[float, float]]:
    """Build the preregistered finite-tail CDF anchors from NBM quantiles."""
    values = [p10_f, p25_f, p50_f, p75_f, p90_f]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("quantiles must be finite")
    if values != sorted(values):
        raise ValueError("quantiles must be monotonic")
    if minimum_tail_width_f <= 0:
        raise ValueError("minimum tail width must be positive")
    lower_width = max(minimum_tail_width_f, (p25_f - p10_f) * (2.0 / 3.0))
    upper_width = max(minimum_tail_width_f, (p90_f - p75_f) * (2.0 / 3.0))
    return [
        (0.0, p10_f - lower_width),
        (0.10, p10_f),
        (0.25, p25_f),
        (0.50, p50_f),
        (0.75, p75_f),
        (0.90, p90_f),
        (1.0, p90_f + upper_width),
    ]


def quantile_preserving_cdf(value: float, anchors: Sequence[tuple[float, float]]) -> float:
    """Evaluate a right-continuous piecewise-linear CDF with explicit atoms."""
    if not math.isfinite(value) or len(anchors) < 2:
        raise ValueError("invalid CDF value or anchors")
    probabilities = [point[0] for point in anchors]
    temperatures = [point[1] for point in anchors]
    if probabilities != sorted(probabilities) or temperatures != sorted(temperatures):
        raise ValueError("CDF anchors must be monotonic")
    if probabilities[0] != 0 or probabilities[-1] != 1:
        raise ValueError("CDF anchors must span probabilities zero to one")
    if value < temperatures[0]:
        return 0.0
    if value >= temperatures[-1]:
        return 1.0

    grouped: list[tuple[float, float, float]] = []
    for probability, temperature in anchors:
        if grouped and grouped[-1][0] == temperature:
            old_temperature, low_probability, _ = grouped[-1]
            grouped[-1] = (old_temperature, low_probability, probability)
        else:
            grouped.append((temperature, probability, probability))
    for index, (temperature, _, high_probability) in enumerate(grouped):
        if value == temperature:
            return high_probability
        if value < temperature:
            left_temperature, _, left_high = grouped[index - 1]
            right_low = grouped[index][1]
            fraction = (value - left_temperature) / (temperature - left_temperature)
            return left_high + fraction * (right_low - left_high)
    return 1.0


def quantile_bucket_probabilities(
    buckets: Sequence[Mapping[str, Any]],
    quantiles_f: Mapping[str, float],
    precision_f: float = 1.0,
    minimum_tail_width_f: float = 1.0,
) -> list[dict[str, Any]]:
    """Attach bucket masses from the locked NBM quantile-preserving CDF."""
    validate_bucket_partition(buckets, precision_f)
    anchors = quantile_cdf_anchors(
        quantiles_f["p10_f"],
        quantiles_f["p25_f"],
        quantiles_f["p50_f"],
        quantiles_f["p75_f"],
        quantiles_f["p90_f"],
        minimum_tail_width_f,
    )
    output = []
    for bucket in buckets:
        lower = bucket["lower_bound"]
        upper = bucket["upper_bound"]
        lower_probability = (
            0.0
            if lower is None
            else quantile_preserving_cdf(lower - precision_f / 2, anchors)
        )
        upper_probability = (
            1.0
            if upper is None
            else quantile_preserving_cdf(upper + precision_f / 2, anchors)
        )
        probability = upper_probability - lower_probability
        if probability < 0 or probability > 1:
            raise ValueError("quantile bucket probability outside [0, 1]")
        output.append({**bucket, "model_probability": probability})
    total = math.fsum(row["model_probability"] for row in output)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"quantile bucket probabilities do not sum to one: {total}")
    return output


def total_variation_distance(
    left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]
) -> float:
    """Compare aligned categorical probability vectors."""
    left_by_market = {str(row["market_id"]): float(row["model_probability"]) for row in left}
    right_by_market = {
        str(row["market_id"]): float(row["model_probability"]) for row in right
    }
    if left_by_market.keys() != right_by_market.keys():
        raise ValueError("probability vectors have different market identities")
    return 0.5 * math.fsum(
        abs(left_by_market[key] - right_by_market[key]) for key in left_by_market
    )


def ask_depth_vwap(
    asks: Sequence[Mapping[str, Any]], notional_usd: Decimal
) -> dict[str, Any]:
    """Walk best-first asks for a fixed-dollar buy; never invent missing depth."""
    if notional_usd <= 0:
        raise ValueError("notional must be positive")
    normalized = []
    for level in asks:
        price = Decimal(str(level["price"]))
        size = Decimal(str(level["size"]))
        if not Decimal("0") < price < Decimal("1") or size <= 0:
            raise ValueError("ask price/size outside valid bounds")
        normalized.append((price, size))
    normalized.sort(key=lambda item: item[0])
    remaining = notional_usd
    shares = Decimal("0")
    fills = []
    for price, available_shares in normalized:
        if remaining <= 0:
            break
        level_cost = price * available_shares
        spent = min(remaining, level_cost)
        filled_shares = spent / price
        shares += filled_shares
        remaining -= spent
        fills.append(
            {
                "price": str(price),
                "shares": str(filled_shares),
                "cost_usd": str(spent),
            }
        )
    if remaining > Decimal("0"):
        return {
            "executable": False,
            "requested_notional_usd": str(notional_usd),
            "available_notional_usd": str(notional_usd - remaining),
            "filled_shares": str(shares),
            "vwap": None,
            "best_ask": str(normalized[0][0]) if normalized else None,
            "slippage": None,
            "fills": fills,
        }
    vwap = notional_usd / shares
    best_ask = normalized[0][0]
    return {
        "executable": True,
        "requested_notional_usd": str(notional_usd),
        "available_notional_usd": str(notional_usd),
        "filled_shares": str(shares),
        "vwap": str(vwap),
        "best_ask": str(best_ask),
        "slippage": str(vwap - best_ask),
        "fills": fills,
    }


def taker_fee_usd(fills: Sequence[Mapping[str, Any]], fee_rate: Decimal) -> Decimal:
    """Apply the documented per-fill C × rate × p × (1-p) taker fee."""
    if fee_rate < 0:
        raise ValueError("fee rate cannot be negative")
    fee = Decimal("0")
    for fill in fills:
        price = Decimal(str(fill["price"]))
        shares = Decimal(str(fill["shares"]))
        if not Decimal("0") < price < Decimal("1") or shares <= 0:
            raise ValueError("fee fill price/size outside valid bounds")
        fee += shares * fee_rate * price * (Decimal("1") - price)
    return fee
