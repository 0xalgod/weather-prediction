# Chicago historical CLOB price coverage

**Experiment:** `EXP-20260903-chicago-historical-price-coverage`  
**Data cut-off:** 2026-09-03 11:30 UTC  
**Decision:** `HISTORICAL_PRICE_COVERAGE_PASS`  
**Trading authorization:** none

## Question

Can the frozen closed-market inventory and Polymarket's public price-history endpoint provide enough historical Chicago market observations to start model research while prospective L2 evidence accumulates?

## Locked design

The latest 30 eligible resolved Chicago maximum-temperature events were selected deterministically from the corrected immutable Gamma inventory. Every YES token was queried from event creation to close with the documented CLOB `prices-history` endpoint using `interval=all` and one-minute fidelity. Empty/error responses remained in the denominator.

## Result

| Metric | Result |
|---|---:|
| Events | 30 |
| Date range | 2026-07-30–2026-08-28 |
| Bucket markets / YES tokens | 330 |
| Events with history | 100% |
| Tokens with history | 100% |
| Request errors | 0% |
| Out-of-window points | 0% |
| Total points | 1,303 |
| Points per token | min 3, median 4, max 4 |

All pre-registered coverage gates passed. There were no duplicate/conflicting timestamps and every multi-point response was strictly increasing.

## What this means

We can immediately build a leakage-safe **indicative-price** research table for 30 consecutive Chicago dates. This is enough to test joining logic, forecast baselines, outcome labels and preliminary calibration—not enough for a reliable trained strategy.

The endpoint returned only 3–4 points per token despite one-minute fidelity. The observed series is therefore sparse/aggregated rather than a historical one-minute order book. It contains no historical bid, ask, spread, depth, trade side, size or fill status. Mid/indicative prices must not be treated as executable entry prices, and this result is not evidence of trading edge.

## Decision and next experiment

Historical research proceeds in parallel with the prospective paper cohort. The next bounded experiment will measure whether as-issued NOAA forecast records and eligible settlement labels can be joined, without look-ahead, to these same 30 locked dates. Economic P&L remains dependent on prospective L2 evidence or a separately validated conservative execution proxy.

Primary documentation:

- [Polymarket price history](https://docs.polymarket.com/api-reference/markets/get-prices-history)
- [Polymarket market-data overview](https://docs.polymarket.com/market-data/overview)
