# EXP-20260830 Phase 3 — Heartbeat, delta replay and REST-anchor shakeout

**Status:** `PASSED` for the bounded shakeout; Phase 3 remains `IN_PROGRESS`  
**Run:** `run=20260830T-phase3-shakeout-v1`  
**Data cut-off:** 2026-08-30T11:37:49Z  
**Capital/orders:** none; public read-only market data only

## Pre-registered hypothesis and thresholds

Hypothesis: after authoritative full books, the public market channel can sustain heartbeat and
apply price deltas into a deterministic per-asset book that reconciles with fresh REST state.

Before capture, the 35-second shakeout was required to meet all of these thresholds:

- 12/12 selected assets receive full books within 15 seconds;
- at least 3 client `PING` messages and 2 server `PONG` messages;
- at least one real price change is applied;
- zero deltas before the relevant full book;
- zero mismatches between replayed and event-advertised best bid/ask; and
- at least 90% of final asset states match fresh REST by hash or executable top of book.

Passing this spike does not satisfy the pre-registered 24-hour uptime gate.

## Sample and method

The selector ranked the committed REST sample's two-sided tokens by spread and depth, then selected
12 assets spanning six markets and three cities: Panama City, Mexico City and Toronto. The client:

1. persisted exact incoming frames with connection-local sequence, receipt UTC and SHA-256;
2. initialized each asset only from a full `book`;
3. sent the documented text `PING` every 10 seconds;
4. applied `BUY` changes to bids and `SELL` changes to asks, deleting size-zero levels;
5. versioned tick-size changes if received; and
6. fetched all 12 REST books concurrently after capture for a final state anchor.

## Results

| Metric | Result | Threshold |
|---|---:|---:|
| Full-book coverage | 12/12 | 12/12 |
| Capture duration | 35.083 s | 35 s target |
| Heartbeats sent / PONG received | 3 / 3 | ≥3 / ≥2 |
| Price-change events | 39 | ≥1 applied change |
| Applied level changes | 78 | ≥1 |
| Delta before base | 0 | 0 |
| Advertised top mismatch | 0 | 0 |
| REST hash-or-top reconciliation | 12/12 (100%) | ≥90% |
| Exact REST hash match | 12/12 (100%) | diagnostic |
| Exact REST top match | 12/12 (100%) | diagnostic |
| Tick-size changes observed | 0 | diagnostic |

The raw WebSocket stream contained 43 frames and 73,098 bytes. All 43 frame checksums were
recomputed successfully. The median inter-frame gap was 0.0435 seconds and the maximum was 4.9662
seconds; the 12 concurrent REST anchors occupied 61,056 bytes. These are short-run diagnostics, not
estimates of daily storage or uptime.

## Interpretation

This is stronger evidence than the reconnect-only spike: real deltas were applied and the resulting
books matched the exchange's REST hashes exactly for every sampled asset. It supports the chosen
full-book-plus-delta state model and the 10-second application heartbeat.

It does not show a trading edge. Several selected books were near terminal probabilities, and the
selection came from an earlier snapshot rather than a locked representative liquidity sample.
Moreover, 35 seconds cannot reveal memory growth, long outages, reconnect storms, market lifecycle
changes or daily storage load.

## Quality controls and limitations

- State remains fail-closed after reconnect; an asset delta cannot create a missing base book.
- Decimal prices are used in replay; size-zero changes remove levels.
- Event-advertised top-of-book is checked after the complete event batch, avoiding false mismatch
  signals while multiple changes in one event are applied atomically.
- No tick-size-change event occurred, so that path remains contract-tested but not empirically seen.
- The current collector exits on an unexpected socket failure. The 24-hour runner still needs
  bounded retry/backoff, reconnect/gap accounting, periodic anchors and checkpoint summaries.

## Decision and next step

The bounded shakeout is `PASSED`. Build the resumable 24-hour stability runner with periodic REST
anchors and explicit uptime, retry, gap, stale-state, bytes and storage metrics. Phase 3 must remain
`IN_PROGRESS` until the registered uptime ≥99% and coverage ≥95% gate is actually measured.
