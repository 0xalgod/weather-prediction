import copy
import hashlib
import json
import unittest
from pathlib import Path

from weather_quant.ingestion.polymarket_orderbook import OrderBookError, normalize_book, normalize_tick_size


FIXTURE = Path(__file__).parent / "fixtures" / "clob_book.json"


def envelope(payload):
    raw = json.dumps(payload, sort_keys=True).encode()
    return {"payload": payload, "requested_at_utc": "2026-01-01T00:00:00Z", "received_at_utc": "2026-01-01T00:00:01Z", "content_sha256": hashlib.sha256(raw).hexdigest()}


class OrderBookTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_normalizes_best_first_and_computes_executable_spread(self):
        book = normalize_book(envelope(self.payload), "token-yes")
        self.assertEqual((book["best_bid"], book["best_ask"], book["spread"]), ("0.45", "0.55", "0.10"))
        self.assertEqual(book["quality"], "TWO_SIDED_BOOK")

    def test_one_sided_book_has_no_spread(self):
        payload = copy.deepcopy(self.payload)
        payload["bids"] = []
        book = normalize_book(envelope(payload), "token-yes")
        self.assertEqual(book["quality"], "ONE_SIDED_BOOK")
        self.assertIsNone(book["spread"])

    def test_asset_mismatch_and_invalid_level_fail_closed(self):
        with self.assertRaisesRegex(OrderBookError, "asset_id mismatch"):
            normalize_book(envelope(self.payload), "different")
        payload = copy.deepcopy(self.payload)
        payload["asks"][0]["size"] = "0"
        with self.assertRaisesRegex(OrderBookError, "outside valid bounds"):
            normalize_book(envelope(payload), "token-yes")

    def test_dynamic_tick_size_is_validated(self):
        self.assertEqual(str(normalize_tick_size({"payload": {"minimum_tick_size": 0.001}})), "0.001")
        with self.assertRaisesRegex(OrderBookError, "outside valid bounds"):
            normalize_tick_size({"payload": {"minimum_tick_size": 0}})


if __name__ == "__main__":
    unittest.main()
