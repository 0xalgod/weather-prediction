import json
import unittest
from pathlib import Path

from weather_quant.ingestion.polymarket_websocket import (
    RecoveryState,
    WebSocketContractError,
    apply_events,
    book_top,
    decode_market_frame,
    raw_event_record,
)

FIXTURE = Path(__file__).parent / "fixtures" / "clob_market_ws_initial.json"


class MarketWebSocketTests(unittest.TestCase):
    def test_initial_array_builds_authoritative_state(self):
        state = RecoveryState(frozenset({"token-yes", "token-no"}))
        apply_events(state, decode_market_frame(FIXTURE.read_text(encoding="utf-8")))
        self.assertTrue(state.ready)
        self.assertEqual(state.delta_before_book_count, 0)
        self.assertEqual(
            book_top(state.books["token-yes"]),
            {"best_bid": "0.45", "best_ask": "0.55"},
        )

    def test_delta_before_book_is_flagged_and_tick_is_versioned(self):
        state = RecoveryState(frozenset({"token-yes"}))
        state.apply({"event_type": "price_change", "price_changes": [{"asset_id": "token-yes"}]})
        state.apply(
            {
                "event_type": "tick_size_change",
                "asset_id": "token-yes",
                "new_tick_size": "0.001",
            }
        )
        self.assertFalse(state.ready)
        self.assertEqual(state.delta_before_book_count, 1)
        self.assertEqual(state.ticks["token-yes"], "0.001")

    def test_price_changes_update_and_remove_levels(self):
        state = RecoveryState(frozenset({"token-yes", "token-no"}))
        apply_events(state, decode_market_frame(FIXTURE.read_text(encoding="utf-8")))
        state.apply(
            {
                "event_type": "price_change",
                "price_changes": [
                    {
                        "asset_id": "token-yes",
                        "side": "BUY",
                        "price": "0.45",
                        "size": "0",
                        "best_bid": "0.46",
                        "best_ask": "0.55",
                    },
                    {
                        "asset_id": "token-yes",
                        "side": "BUY",
                        "price": "0.46",
                        "size": "8",
                        "best_bid": "0.46",
                        "best_ask": "0.55",
                    },
                ],
            }
        )
        self.assertEqual(
            book_top(state.books["token-yes"]),
            {"best_bid": "0.46", "best_ask": "0.55"},
        )
        self.assertEqual(state.applied_change_count, 2)
        self.assertEqual(state.advertised_top_mismatch_count, 0)

    def test_pong_and_raw_checksum_are_preserved(self):
        self.assertEqual(decode_market_frame("PONG"), [{"event_type": "pong"}])
        record = raw_event_record("PONG", "connection-1", 1, "2026-01-01T00:00:00Z")
        self.assertEqual(len(record["content_sha256"]), 64)
        self.assertEqual(record["raw"], "PONG")

    def test_invalid_frame_fails_closed(self):
        with self.assertRaisesRegex(WebSocketContractError, "neither PONG nor JSON"):
            decode_market_frame("not-json")
        with self.assertRaisesRegex(WebSocketContractError, "must be objects"):
            decode_market_frame(json.dumps([1]))


if __name__ == "__main__":
    unittest.main()
