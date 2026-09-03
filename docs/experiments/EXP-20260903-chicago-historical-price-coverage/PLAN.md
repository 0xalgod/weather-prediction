# EXP-20260903 — Chicago historical price coverage

**Status:** `PASSED`
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

## Execution log

### 2026-09-03 — Attempt 1 incomplete before network requests

- The frozen Gamma inventory contained `creationDate=2026-08-23T00:57:43.55602Z`; Python 3.9 `datetime.fromisoformat` rejected its five-digit fractional seconds.
- Failure occurred during sample expansion before run-directory creation and before any experiment-specific CLOB request or price observation.
- Corrective scope is locked to padding 1–5 fractional-second digits to six before standard parsing and adding a regression test. Sample, endpoint, windows, metrics and thresholds are unchanged.

### 2026-09-03 — Attempt 2 accepted

- All locked checks passed for 30 events, 330 YES tokens and 1,303 points: event/token coverage 100%, errors 0%, out-of-window points 0% and minimum 3 points per covered token.
- Event dates span 2026-07-30 through 2026-08-28; every event has 11 bucket markets.
- Coverage is sparse: 17 tokens have 3 points and 313 have 4; median 4. No duplicate/conflicting timestamps or response-order defects were observed.
- Decision: `HISTORICAL_PRICE_COVERAGE_PASS`, limited to indicative-price/forecast research. This does not pass executable historical P&L or edge gates.
- Next: pre-register and measure an as-issued forecast + eligible outcome join on these exact event identities/dates.
