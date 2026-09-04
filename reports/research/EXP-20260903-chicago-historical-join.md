# Chicago historical forecast/outcome join

**Experiment:** `EXP-20260903-chicago-historical-join`  
**Accepted run:** attempt 2  
**Decision:** `HISTORICAL_JOIN_PASS`  
**Trading authorization:** none

## Result

The exact 30 dates locked by the preceding historical-price experiment now have a complete forecast/outcome join.

| Check | Result |
|---|---:|
| Frozen event identities | 30/30 |
| NBM 07Z objects | 30/30 |
| KORD parse + exact target record | 30/30 |
| Publication proxy after decision time | 0 |
| Exactly one resolved winner | 30/30 |
| Valid exhaustive bucket partition | 30/30 |
| Final eligible joins | 30/30 |

The dates span 2026-07-30 through 2026-08-28. Every forecast is NBM v5.0, forecast hour 41, and contains mean, standard deviation plus p10/p25/p50/p75/p90. Accepted source bytes total 1,041,734,375.

## Attempt history

Attempt 1 passed identity/outcome/parse checks for 23 dates but five reads timed out and two connections reset. Its raw decision remains `HISTORICAL_JOIN_FAIL`. Attempt 2 checksum-verified and reused those 23 complete objects, retrieved only the same seven failed objects with lower concurrency/longer timeout, and passed 30/30. No dates, values, thresholds or forecast cycles changed.

## What this unlocks

We can now calculate, on the same resolved days:

- Gaussian and quantile probability assigned to the actual winning bucket;
- multiclass log loss, Brier score and ranked probability score;
- calibration diagnostics with strong small-sample warnings;
- comparison against the latest sparse indicative market probability available by the locked decision time.

## Remaining boundary

This is not yet a trained model or profitable backtest. Historical CLOB points are not executable bid/ask fills, and 30 consecutive summer dates are too few and too concentrated for a robust edge claim. The NBM f41-to-Chicago-local-day mapping also remains provisional pending independent product-semantics reconciliation.
