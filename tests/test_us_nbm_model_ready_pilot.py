import pytest

from scripts.build_us_nbm_model_ready_pilot import normalized_prices


def test_normalized_prices_preserve_bucket_order_and_raw_sum():
    event = {"buckets": [{"market_id": "a"}, {"market_id": "b"}]}
    price = {"points": [{"market_id": "b", "price": 0.6}, {"market_id": "a", "price": 0.3}]}
    normalized, raw_sum = normalized_prices(event, price)
    assert raw_sum == pytest.approx(0.9)
    assert normalized == pytest.approx([1 / 3, 2 / 3])
