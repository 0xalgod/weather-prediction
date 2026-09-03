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
