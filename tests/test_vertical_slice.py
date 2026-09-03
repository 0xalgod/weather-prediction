from decimal import Decimal

import pytest

from weather_quant.market_model.vertical_slice import (
    ask_depth_vwap,
    bucket_probability,
    gaussian_bucket_probabilities,
    normal_cdf,
)


def bucket(label, lower, upper, market_id):
    return {
        "label": label,
        "lower_bound": lower,
        "upper_bound": upper,
        "lower_inclusive": True,
        "upper_inclusive": True,
        "market_id": market_id,
        "condition_id": f"condition-{market_id}",
        "yes_token_id": f"yes-{market_id}",
        "no_token_id": f"no-{market_id}",
    }


def partition():
    return [
        bucket("69°F or below", None, 69, "1"),
        bucket("70-71°F", 70, 71, "2"),
        bucket("72-73°F", 72, 73, "3"),
        bucket("74°F or higher", 74, None, "4"),
    ]


def test_normal_cdf_is_centered_and_rejects_invalid_sigma():
    assert normal_cdf(72, 72, 3) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="positive"):
        normal_cdf(72, 72, 0)


def test_tail_and_finite_bucket_probabilities_use_half_degree_boundaries():
    lower = bucket_probability(None, 69, 72, 3)
    middle = bucket_probability(70, 71, 72, 3)
    upper = bucket_probability(74, None, 72, 3)
    assert 0 < lower < 1
    assert 0 < middle < 1
    assert 0 < upper < 1


def test_exhaustive_bucket_probabilities_sum_to_one():
    rows = gaussian_bucket_probabilities(partition(), 72, 3)
    assert sum(row["model_probability"] for row in rows) == pytest.approx(1.0)
    assert all(0 <= row["model_probability"] <= 1 for row in rows)


def test_partition_gap_is_rejected():
    broken = partition()
    broken[2]["lower_bound"] = 73
    with pytest.raises(ValueError, match="gap or overlap"):
        gaussian_bucket_probabilities(broken, 72, 3)


def test_single_level_vwap_uses_executable_ask_not_midpoint():
    result = ask_depth_vwap([{"price": "0.25", "size": "100"}], Decimal("10"))
    assert result["executable"] is True
    assert Decimal(result["vwap"]) == Decimal("0.25")
    assert Decimal(result["filled_shares"]) == Decimal("40")
    assert result["slippage"] == "0.00"


def test_multi_level_vwap_walks_depth_best_first():
    asks = [
        {"price": "0.30", "size": "100"},
        {"price": "0.20", "size": "25"},
    ]
    result = ask_depth_vwap(asks, Decimal("10"))
    assert result["executable"] is True
    assert len(result["fills"]) == 2
    assert Decimal(result["vwap"]) > Decimal("0.20")
    assert Decimal(result["slippage"]) > 0


def test_insufficient_depth_is_explicit_and_has_no_vwap():
    result = ask_depth_vwap([{"price": "0.25", "size": "4"}], Decimal("10"))
    assert result["executable"] is False
    assert result["available_notional_usd"] == "1.00"
    assert result["vwap"] is None


@pytest.mark.parametrize(
    "asks",
    [
        [{"price": "0", "size": "1"}],
        [{"price": "1", "size": "1"}],
        [{"price": "0.5", "size": "0"}],
    ],
)
def test_invalid_ask_levels_fail_closed(asks):
    with pytest.raises(ValueError, match="outside valid bounds"):
        ask_depth_vwap(asks, Decimal("10"))
