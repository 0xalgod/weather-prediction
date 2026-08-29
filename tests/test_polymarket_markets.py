import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from weather_quant.ingestion.polymarket_markets import (
    DiscoveryError,
    GammaDiscoveryClient,
    normalize_highest_temperature_event,
    parse_json_array,
    summarize_discovery,
    write_raw_envelope,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "gamma_highest_temperature_page.json"
FIXED_TIME = datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc)


class GammaDiscoveryClientTest(unittest.TestCase):
    def test_keyset_pagination_preserves_cursor_and_raw_hash(self) -> None:
        calls = []
        responses = [
            {"events": [], "next_cursor": "cursor-1"},
            {"events": [], "next_cursor": None},
        ]

        def requester(url, headers, timeout):
            calls.append((url, headers, timeout))
            return json.dumps(responses[len(calls) - 1], separators=(",", ":")).encode("utf-8")

        client = GammaDiscoveryClient(requester=requester, clock=lambda: FIXED_TIME)
        envelopes = list(client.iter_event_envelopes(page_size=500, max_pages=3))

        self.assertEqual(len(envelopes), 2)
        first_query = parse_qs(urlparse(calls[0][0]).query)
        second_query = parse_qs(urlparse(calls[1][0]).query)
        self.assertEqual(first_query["tag_slug"], ["highest-temperature"])
        self.assertEqual(first_query["closed"], ["false"])
        self.assertEqual(first_query["limit"], ["500"])
        self.assertNotIn("after_cursor", first_query)
        self.assertEqual(second_query["after_cursor"], ["cursor-1"])
        self.assertEqual(len(envelopes[0]["content_sha256"]), 64)
        self.assertEqual(envelopes[0]["requested_at_utc"], "2026-08-29T00:00:00Z")

    def test_cursor_loop_is_rejected(self) -> None:
        payload = json.dumps({"events": [], "next_cursor": "repeat"}).encode("utf-8")
        client = GammaDiscoveryClient(
            requester=lambda url, headers, timeout: payload,
            clock=lambda: FIXED_TIME,
        )
        with self.assertRaisesRegex(DiscoveryError, "cursor loop"):
            list(client.iter_event_envelopes(max_pages=3))


class MarketNormalizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_valid_event_maps_binary_outcomes_to_tokens(self) -> None:
        normalized = normalize_highest_temperature_event(
            self.fixture["events"][0],
            as_of=datetime(2026, 8, 28, tzinfo=timezone.utc),
        )

        self.assertEqual(normalized.event["city_label"], "NYC")
        self.assertTrue(normalized.event["temporally_relevant"])
        self.assertEqual(len(normalized.markets), 1)
        self.assertTrue(normalized.markets[0]["eligible_for_book_collection"])
        self.assertEqual([row["outcome_label"] for row in normalized.outcomes], ["Yes", "No"])
        self.assertEqual([row["token_id"] for row in normalized.outcomes], ["token-yes-1", "token-no-1"])
        self.assertEqual(normalized.exclusions, ())

    def test_stale_missing_identifier_market_has_explicit_reasons(self) -> None:
        normalized = normalize_highest_temperature_event(
            self.fixture["events"][1],
            as_of=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )

        self.assertFalse(normalized.event["temporally_relevant"])
        self.assertFalse(normalized.markets[0]["eligible_for_book_collection"])
        reasons = normalized.exclusions[0]["reason_codes"]
        self.assertIn("EVENT_END_DATE_PASSED", reasons)
        self.assertIn("MISSING_CONDITION_ID", reasons)
        self.assertIn("MISSING_CLOB_TOKEN_IDS", reasons)
        self.assertIn("OUTCOME_TOKEN_LENGTH_MISMATCH", reasons)
        self.assertEqual(normalized.outcomes, ())

    def test_summary_uses_event_cluster_counts(self) -> None:
        events = [
            normalize_highest_temperature_event(
                event,
                as_of=datetime(2026, 8, 28, tzinfo=timezone.utc),
            )
            for event in self.fixture["events"]
        ]
        summary = summarize_discovery(events)

        self.assertEqual(summary["event_count"], 2)
        self.assertEqual(summary["unique_city_count"], 2)
        self.assertEqual(summary["market_count"], 2)
        self.assertEqual(summary["eligible_market_count"], 1)
        self.assertEqual(summary["identifier_complete_market_count"], 1)
        self.assertEqual(summary["excluded_market_count"], 1)
        self.assertEqual(summary["outcome_count"], 2)

    def test_invalid_json_array_is_rejected(self) -> None:
        with self.assertRaisesRegex(DiscoveryError, "not valid JSON"):
            parse_json_array("not-json", "outcomes")

    def test_expired_market_keeps_valid_historical_outcome_mapping(self) -> None:
        normalized = normalize_highest_temperature_event(
            self.fixture["events"][0],
            as_of=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )

        self.assertTrue(normalized.markets[0]["identifier_complete"])
        self.assertFalse(normalized.markets[0]["eligible_for_book_collection"])
        self.assertEqual(len(normalized.outcomes), 2)
        self.assertEqual(
            normalized.exclusions[0]["reason_codes"],
            ["EVENT_END_DATE_PASSED"],
        )

    def test_raw_envelope_is_immutable(self) -> None:
        envelope = {"content_sha256": "abc", "payload": {"events": []}}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "page.json"
            write_raw_envelope(envelope, destination)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), envelope)
            with self.assertRaises(FileExistsError):
                write_raw_envelope(envelope, destination)


if __name__ == "__main__":
    unittest.main()
