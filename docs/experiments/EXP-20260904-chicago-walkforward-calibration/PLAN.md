# EXP-20260904 — Chicago walk-forward probability calibration

**Status:** `IN_PROGRESS`
**Pre-registration:** 2026-09-04, before retrieval/scoring of the expanded 114-date forecast sample

## Objective

Test whether simple, interpretable station/outcome calibration improves the fixed NBM Gaussian and quantile proxy distributions on genuinely future Chicago events.

## Locked universe

- Frozen corrected Gamma inventory, Chicago maximum-temperature events dated 2026-05-06 through 2026-08-28 inclusive.
- Deterministic eligibility rules produce 114 resolved events with 11 Fahrenheit buckets each. The calendar range contains no eligible event on 2026-06-18; dates are ordered but not claimed continuous.
- This window stays within NBM v5.0. Missing or invalid dates remain missing; no replacement/backfill.
- Forecast input is prior-day 07Z KORD NBP f41, explicitly labelled `PROXY_18H_MAX`; HTTP Last-Modified must be at/before prior-day 11:00 UTC.
- Outcomes are exact terminal winners from frozen Gamma metadata.

## Locked retrieval policy

- Checksum-verify and reuse the accepted 30-date join sources.
- Download only the remaining 84 prior-day 07Z objects with four workers and 300-second request timeout.
- Permit at most three attempts per object only for timeout, connection-reset or URL transport errors.
- Every attempt has a distinct immutable filename. Partial attempts are retained but never accepted or parsed.
- HTTP missing objects and semantic/parse failures are not replaced by another cycle or date.

## Execution log

### 2026-09-04 — Dataset attempt 1 stopped before download

- The initial selector admitted an archived duplicate for 2026-05-19 before applying the complete event-level eligibility contract.
- Event `493662` has an `arch-` slug and lacks `closedTime`/`automaticallyResolved`; canonical event `503629` has both fields and remains eligible.
- The already measured strict eligibility set contains 114 unique dates; 2026-06-18 is missing. No NOAA download or forecast value was observed in this attempt.
- Correction applies the pre-registered closed/automatically-resolved/closed-time/all-markets-UMA-resolved gate before duplicate-date validation. Expected count, model, dates, thresholds and retrieval policy are unchanged.

## Walk-forward design

- Sort 114 events by target date.
- First 60 form the initial training history.
- Evaluate the remaining expected 54 one at a time.
- Before each OOS event, refit using only all earlier events; never train on the current/future outcome.
- The OOS stream is the primary result. No random split.

## Models and locked calibration grid

Raw Gaussian and raw quantile-preserving distributions remain baselines.

For each model, search shift `−5.0°F` through `+5.0°F` in `0.5°F` steps and spread scale `{0.75, 1.0, 1.25}` using train mean multiclass log loss. Gaussian shifts mean and scales SD. Quantile calibration shifts the median and scales each quantile's deviation from that median.

Ties choose minimum absolute shift, then scale closest to 1, then numeric order. The grid is never expanded after seeing OOS scores.

## Metrics and gates

Primary: OOS mean multiclass log loss. Secondary: Brier, RPS and winning-bucket probability. Paired event/date bootstrap: 10,000 samples, seed `20260904`.

Data gate requires ≥99% eligible events and at least 53 OOS predictions. A calibrated model is practically improved only if it achieves:

- ≥2% relative log-loss improvement over its own raw counterpart; and
- OOS Brier difference ≤0.

Strong evidence additionally requires the paired calibrated-minus-raw log-loss 95% CI upper bound below zero. Otherwise the result is preliminary/uncertain.

## Boundaries

This experiment trains forecast calibration, not a trading strategy. It uses no historical market-price comparison, EV, fills or orders. The one-city, one-season, one-model-version sample limits external validity; any later strategy selection requires independent prospective market data and broader OOS regimes.
