from scripts.evaluate_us_pilot_price_eligibility import eligibility_reason


def test_price_eligibility_reasons_are_fail_closed():
    assert eligibility_reason({"complete_vector": False, "usable_full_vector": False}) == (
        "NO_TRADE_INCOMPLETE_VECTOR"
    )
    assert eligibility_reason({"complete_vector": True, "usable_full_vector": False}) == (
        "NO_TRADE_STALE_VECTOR"
    )
    assert eligibility_reason({"complete_vector": True, "usable_full_vector": True}) == (
        "PRICE_ELIGIBLE"
    )
