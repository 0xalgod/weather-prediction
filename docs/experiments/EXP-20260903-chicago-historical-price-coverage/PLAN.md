# EXP-20260903 — Chicago historical price coverage

**Status:** `IN_PROGRESS`  
**Pre-registration time:** 2026-09-03, before experiment-specific CLOB history requests  
**Purpose:** Determine whether existing public historical data can support a fast Chicago backtest without confusing indicative prices with executable fills.

## Hypothesis

For a deterministic sample of the latest 30 eligible closed Chicago maximum-temperature events in the frozen Gamma inventory, the public CLOB price-history endpoint returns at least two timestamped YES-token observations for at least 80% of events and tokens, with request-error rate at most 2% and no observations outside the requested event window.

## Locked sample

- Source: immutable corrected closed inventory run `data/raw/polymarket_gamma/closed=true/run=20260829T215446Z`.
- Cut-off: `2026-09-03T11:30:00Z`.
- Match `chicago` case-insensitively in event title; do not manually choose dates.
- Retain events marked closed whose markets are UMA-resolved and have complete binary outcome/token identities.
- Sort by event end descending and event ID descending; take the first 30. If fewer than 20 events remain, fail sample sufficiency.
- Query every YES token in every selected bucket. Failed or empty tokens remain in the denominator.

## Data request and immutable artifacts

- Endpoint: public `GET https://clob.polymarket.com/prices-history`.
- Parameters: token asset ID as `market`, explicit event creation-to-close Unix window, `interval=all`, `fidelity=1` minute.
- Store each HTTP response with retrieval time, request parameters/status and SHA-256; never overwrite a run.
- Store a normalized event/token coverage table and a machine-readable aggregate report.

## Pre-registered quality metrics and gate

- selected event count ≥20;
- events with any price history ≥80%;
- YES tokens with any price history ≥80%;
- successful covered token has ≥2 timestamped points;
- request error rate ≤2%;
- points outside the requested time window = 0%;
- timestamps strictly increasing after deterministic duplicate handling; duplicate/conflicting timestamps are reported.

Decision values:

- `HISTORICAL_PRICE_COVERAGE_PASS`: every gate passes;
- `HISTORICAL_PRICE_COVERAGE_FAIL`: any gate fails;
- `INCOMPLETE`: runner/data integrity prevents a valid measurement.

## Interpretation boundary

The documented history response contains timestamp and price, not historical bid/ask depth, spread, trade side, available size or fill status. Therefore a pass permits forecast/calibration and **indicative-price** research only. It does not authorize an executable P&L backtest, edge claim, paper-trade replacement or live trading. Economic backtesting must use prospective L2 snapshots or a separately validated conservative execution proxy.

## Next step after this experiment

If coverage passes, join selected event dates and winning buckets to as-issued NOAA forecast availability, then construct the first leakage-safe modeling table. If coverage fails, measure an alternative trade-history source or narrow the historical work to forecast calibration while prospective L2 collection continues.
