# EXP-20260830 Phase 3 — Public WebSocket forced-reconnect recovery

**Status:** `PASSED` for the forced-reconnect spike; Phase 3 remains `IN_PROGRESS`  
**Run:** `run=20260830T-phase3-reconnect-v1`  
**Data cut-off:** 2026-08-30T11:31:33Z  
**Capital/orders:** none; public read-only market data only

## Pre-registered spike hypothesis and threshold

Hypothesis: a public market-channel subscriber can recover authoritative state after a forced
disconnect by resubscribing and waiting for a full `book` for every asset before accepting deltas.

The spike passes only if:

1. both selected assets receive full books on the first and second connections;
2. forced reconnect completes within 15 seconds;
3. no second-connection delta is accepted before its asset has a full book; and
4. the recovered book has either the same hash or the same executable best bid/ask as an
   immediately requested public REST book.

This threshold evaluates recovery only. It does not pass the 24-hour stability or delta-replay gate.

## Sample and method

- Deterministic selection from the committed 66-token REST coverage artifact.
- One Mexico City market (`market_id=3973061`), both Yes and No tokens.
- Connection 1 subscribed and waited for both authoritative full books.
- The client then closed the socket intentionally, waited 0.5 seconds, opened connection 2 and
  discarded any asset-level delta until that asset had a new full book.
- Immediately afterward it requested `/book` for each asset and compared hash and top of book.
- Exact raw WebSocket frames and REST envelopes are immutable local research data. Each WebSocket
  frame has connection-local sequence, receipt UTC and SHA-256.

## Results

| Metric | Connection 1 | Connection 2 |
|---|---:|---:|
| Full books | 2/2 | 2/2 |
| Frames | 1 | 1 |
| Recovery time | 0.416 s | 0.341 s |
| Delta before full book | 0 | 0 |

REST reconciliation was exact for both tokens:

- No token: WebSocket/REST hash `6abd3fd788a54187066ee8b79444f5e998333f0f`; best bid
  `0.999`, no ask.
- Yes token: WebSocket/REST hash `7a9c920d52545f3948c624a12b07bab24cb36c1f`; no bid,
  best ask `0.001`.
- Hash match: 2/2; top-of-book match: 2/2.

The books were one-sided and near terminal prices. They prove transport recovery and exact
point-in-time reconciliation, not useful liquidity or strategy edge.

## Data-quality and reproducibility checks

- JSON array initial frames are expanded into typed events.
- `PONG`, invalid JSON, invalid event arrays, delta-before-base and tick-size changes have contract
  tests.
- Raw frames retain the exact source string and checksum; parser output is not substituted for raw
  evidence.
- Recovery state is reset per connection. A prior connection's book cannot authorize a new
  connection's deltas.
- 39 repository tests pass; focused Ruff checks pass for all new files.

## Decision and limitations

The forced-reconnect substep is `PASSED`: resubscription produced a new full book for every selected
asset and reconciled exactly with REST. Public WebSocket capture is therefore operationally viable
for a prospective collector.

Important limitations remain:

- The short run observed only initial `book` events. No live `price_change` or `tick_size_change`
  arrived, so deterministic delta application has not been empirically validated.
- Two tokens from one market are not a stability sample.
- No heartbeat, provider outage, long gap, stale-state or storage-rate claim can be made.
- No profitability or execution inference follows from this test.

## Next smallest experiment

Implement a bounded collector/replayer that keeps multiple liquid assets subscribed, sends the
documented 10-second `PING`, applies price and tick deltas to per-asset state, periodically anchors
state to REST, and records gap/reconnect/storage metrics. Run a short shakeout first; only then begin
the pre-registered 24-hour stability capture.
