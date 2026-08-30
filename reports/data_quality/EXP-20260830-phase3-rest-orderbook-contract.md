# Phase 3 Public REST Order-Book Contract and Coverage

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Capture date:** 2026-08-30  
**Gamma run:** `20260829T225213Z`  
**CLOB raw run:** `data/raw/polymarket_clob/run=20260830T-phase3-rest-v3`  
**Phase status:** `IN_PROGRESS` — REST substep passed

## Question and acceptance criterion

Can public, unauthenticated CLOB `/book` and `/tick-size/{token_id}` endpoints produce point-in-time, provenance-preserving executable-side snapshots for at least three active weather events, with every returned level validated or explicitly quality-flagged?

This substep required ≥3 active events, 100% requested-token response coverage, immutable raw envelopes, asset-ID integrity, positive size, prices strictly between 0 and 1, current dynamic tick compliance, best-first normalization, and no invented spread for one-sided/empty books.

## Sample

The deterministic sample used the three eligible events with the latest end time in the fresh active Gamma inventory:

- Panama City event `930669`;
- Mexico City event `930668`;
- Toronto event `930667`.

Each contains 11 binary temperature buckets and 22 Yes/No token books, for 66 requested token snapshots.

## Results

| Measure | Result |
|---|---:|
| Successful `/book` + dynamic tick snapshots | 66/66 (100%) |
| Request failures | 0 |
| Two-sided books | 48 (72.73%) |
| One-sided books | 18 (27.27%) |
| Empty/crossed books | 0 / 0 |
| Validated bid levels | 1,914 |
| Validated ask levels | 1,914 |
| Dynamic tick violations | 0 |
| Dynamic tick `0.01` / `0.001` | 38 / 28 tokens |
| Gamma tick different from current CLOB tick | 8 tokens |
| Request latency min / median / max | 134.5 / 147.9 / 201.2 ms |
| Two-sided spread min / median / max | 0.001 / 0.020 / 0.050 |
| Local raw storage | 132 envelopes, approximately 528 KB |

One-sided books have `spread=null`; no midpoint or executable fair value is fabricated. The API level arrays are normalized to best-first order after validation while the immutable raw payload preserves source ordering.

## Invalidated first tick result

The first capture reported 190 tick violations because it compared live levels with Gamma's metadata tick. Official Polymarket documentation and the public market WebSocket contract show that tick size can change from `0.01` to `0.001`; the dedicated public tick-size endpoint returns the current value. That first tick metric is invalid. Corrected runs fetch a checksummed tick-size envelope per token and produce zero violations; 8/66 current values differed from Gamma metadata. V3 additionally persists normalized full levels in the committed coverage artifact for deterministic replay.

Primary documentation:

- [Get order book / public methods](https://docs.polymarket.com/trading/clients/public)
- [Get dynamic tick size](https://docs.polymarket.com/api-reference/market-data/get-tick-size-by-path-parameter)
- [Market WebSocket and tick-size-change event](https://docs.polymarket.com/api-reference/wss/market)
- [CLOB rate limits](https://docs.polymarket.com/api-reference/rate-limits)

## Decision

The REST contract/coverage substep passes. It proves current public executable-side metadata is collectible, not that historical fills are reconstructable or that the 24-hour Phase 3 gate has passed. The 27.27% one-sided rate already demonstrates why midpoint-only backtests would be unsafe.

## Artifacts

- `src/weather_quant/ingestion/polymarket_orderbook.py`
- `schemas/orderbook_snapshot.schema.json`
- `tests/fixtures/clob_book.json`
- `reports/data_quality/EXP-20260830-phase3-rest-book-coverage.json`
- 35 repository tests pass.

## Next action

Implement a public market WebSocket prototype, persist initial full-book plus deltas/tick changes, and reconcile a forced reconnect against a fresh REST snapshot before scheduling the 24-hour collector.
