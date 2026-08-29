import unittest

from weather_quant.normalization.manual_reconciliation import (
    identity_matches,
    parse_resolution_rule,
    parse_wunderground_high,
    outcome_rule_check,
    terminal_winner,
)


class ManualReconciliationTests(unittest.TestCase):
    def test_parses_rule_and_station(self):
        rule = parse_resolution_rule(
            "This resolves to the highest temperature recorded at the Dallas Love Field Station in degrees Fahrenheit on 19 May '26.",
            "https://www.wunderground.com/history/daily/us/tx/dallas/KDAL",
        )
        self.assertEqual((rule["station_code"], rule["unit"]), ("KDAL", "F"))
        self.assertTrue(rule["rule_parse_complete"])

    def test_parses_nws_timeseries_station_query(self):
        rule = parse_resolution_rule(
            "This resolves to the highest temperature recorded at the Chicago O'Hare Station in degrees Fahrenheit on 28 Aug '26.",
            "https://www.weather.gov/wrh/timeseries?site=kord",
        )
        self.assertEqual(rule["station_code"], "KORD")

    def test_parses_visible_daily_high(self):
        self.assertEqual(parse_wunderground_high("<b>Day High &amp; Low</b> High 30°C Low 19°C"), {"value": 30, "unit": "C"})

    def test_requires_one_exact_terminal_winner(self):
        winner, status = terminal_winner([
            {"groupItemTitle": "20°C", "outcomePrices": '["1","0"]'},
            {"groupItemTitle": "21°C", "outcomePrices": '["0","1"]'},
        ])
        self.assertEqual((winner, status), ("20°C", "EXACT_TERMINAL_WINNER"))
        self.assertEqual(terminal_winner([{"outcomePrices": '["0.5","0.5"]'}])[1], "NO_EXACT_TERMINAL_WINNER")

    def test_identity_comparison_accepts_gamma_and_sample_shapes(self):
        sample = [{"market_id": "1", "condition_id": "c", "token_ids": ["a", "b"]}]
        live = [{"id": "1", "conditionId": "c", "clobTokenIds": '["a","b"]'}]
        self.assertTrue(identity_matches(sample, live))

    def test_checks_celsius_and_converted_fahrenheit_buckets(self):
        self.assertEqual(outcome_rule_check("22°C", {"value": 22, "unit": "C"}), "MATCH")
        self.assertEqual(outcome_rule_check("73°F or below", {"value": 30, "unit": "C"}), "MISMATCH")
        self.assertEqual(outcome_rule_check("68°F or higher", {"value": 27, "unit": "C"}), "MATCH")


if __name__ == "__main__":
    unittest.main()
