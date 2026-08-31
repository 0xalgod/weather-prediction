import unittest

from weather_quant.market_model.settlement_audit import (
    city_from_title,
    classify_settlement_record,
    wilson_interval,
)


class SettlementAuditTests(unittest.TestCase):
    def test_classifies_match_and_divergence_from_values(self):
        base = {
            "event_id": "1",
            "title": "Highest temperature in Test City on June 1?",
            "identity_match": True,
            "terminal_status": "EXACT_TERMINAL_WINNER",
            "rule": {"station_code": "KAAA"},
            "observed_high_display": {"value": 12, "unit": "C"},
        }
        match = classify_settlement_record(
            {**base, "terminal_winner_bucket": "10°C or higher"}
        )
        self.assertEqual(match["comparison"], "MATCH")
        self.assertTrue(match["market_terminal_label_available"])
        self.assertTrue(match["current_page_bucket_consistent"])
        self.assertFalse(match["temperature_label_eligible"])
        mismatch = classify_settlement_record(
            {**base, "terminal_winner_bucket": "9°C or below"}
        )
        self.assertEqual(mismatch["comparison"], "MISMATCH")
        self.assertTrue(mismatch["market_terminal_label_available"])
        self.assertFalse(mismatch["current_page_bucket_consistent"])
        self.assertFalse(mismatch["temperature_label_eligible"])

    def test_ineligible_record_preserves_reason(self):
        record = {
            "event_id": "1",
            "title": "Highest temperature in Test City on June 1?",
            "identity_match": True,
            "terminal_status": "NO_EXACT_TERMINAL_WINNER",
            "observed_high_display": {"value": 12, "unit": "C"},
            "terminal_winner_bucket": None,
            "rule": {"station_code": "KAAA"},
            "disposition": "NON_TERMINAL_OR_CANCELLED",
        }
        result = classify_settlement_record(record)
        self.assertEqual(result["comparison"], "INELIGIBLE")
        self.assertEqual(result["disposition"], "NON_TERMINAL_OR_CANCELLED")

    def test_wilson_interval_contains_observed_rate(self):
        lower, upper = wilson_interval(3, 15)
        self.assertLess(lower, 0.2)
        self.assertGreater(upper, 0.2)

    def test_city_parser_fails_closed(self):
        self.assertEqual(
            city_from_title("Highest temperature in Buenos Aires on January 1?"),
            "Buenos Aires",
        )
        with self.assertRaises(ValueError):
            city_from_title("Unrelated market")


if __name__ == "__main__":
    unittest.main()
