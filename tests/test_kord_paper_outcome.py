from scripts.reconcile_kord_paper_outcome import gamma_winner, noaa_maximum_f


def test_noaa_maximum_rounds_each_observation_to_whole_fahrenheit() -> None:
    payload = {
        "features": [
            {"properties": {"timestamp": "a", "temperature": {"value": 32.8}}},
            {"properties": {"timestamp": "b", "temperature": {"value": 33.3}}},
        ]
    }
    maximum, rows = noaa_maximum_f(payload)
    assert maximum == 92
    assert len(rows) == 2


def test_gamma_winner_requires_resolved_yes_price() -> None:
    payload = {
        "markets": [
            {"id": "1", "outcomePrices": '["0", "1"]', "umaResolutionStatus": "resolved"},
            {"id": "2", "outcomePrices": '["1", "0"]', "umaResolutionStatus": "resolved"},
        ]
    }
    assert gamma_winner(payload)["id"] == "2"
