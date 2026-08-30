# EXP-20260830 Phase 4 — NBM 365-day coverage and KORD cycle policy

**Status:** `PASSED` for the locked 365-day policy probe; NBM/KORD remains `CONDITIONAL_PASS`  
**Window:** 2025-08-30 through 2026-08-29, 365 completed run dates  
**Primary/fallback order:** 01Z → 07Z → 13Z → 19Z

## Pre-registered hypothesis and gate

For every date in the locked window, a KORD-capable full NBP cycle can be selected without looking
at forecast values, while retaining the selected run's true information time.

The gate required:

- primary 01Z object coverage ≥99%;
- cascading policy coverage =100%;
- zero unresolved/transient request failures; and
- any required fallback must be fully downloaded, checksummed and parsed for KORD before acceptance.

Fallback does not recreate a missing 01Z forecast. It is a different, later information set.

## Daily coverage result

| Metric | Result | Gate |
|---|---:|---:|
| Completed dates | 365 | 365 |
| Primary 01Z | 364 | ≥361.35 (99%) |
| Primary coverage | 99.726% | ≥99% |
| Fallback dates | 1 | diagnostic |
| Unavailable dates | 0 | 0 |
| Policy coverage | 100% | 100% |
| Transient failures after retries | 0 | 0 |

The sole fallback date was 2026-06-01. Its primary 01Z object was HTTP 404 and 07Z was the first
eligible object in the pre-declared fallback order.

## Actual fallback verification

The complete 2026-06-01 07Z bulletin was downloaded:

- size: 34,712,943 bytes;
- SHA-256: `0e15713fb89a1fb45b4343f88ae6b1b15d2128c70f2200cacdd57d947e83f50f`;
- HTTP Last-Modified: 2026-06-01 08:15:34 GMT;
- KORD station block: exactly one, NBM v5.0;
- required mean/SD and five percentile rows: all present;
- parsed KORD MaxT records: 9; missing values: 0.

The first maximum-temperature record is run 07Z, forecast hour 17, valid 2026-06-02 00Z, with
mean/SD 72°F/3°F and 10/25/50/75/90 percentiles 68/70/72/74/76°F.

## Frozen run-selection policy

For KORD NBM baseline construction:

1. Preserve every run independently; never overwrite or relabel a fallback as 01Z.
2. Prefer 01Z only for the daily canonical sample when its object exists.
3. If 01Z is absent, test 07Z, then 13Z, then 19Z in that fixed order.
4. Mark selected non-01Z rows `FALLBACK` and retain their actual model run, object timestamp and
   ingestion/first-seen evidence.
5. A forecast is eligible for a market snapshot only when its measured/conservative availability
   time is not later than the snapshot. The 2026-06-01 07Z fallback cannot be used before its
   observed object timestamp of 08:15:34 UTC.
6. If no eligible run existed by the decision time, the record is missing/`NO_FORECAST`; do not use
   a later fallback and do not impute.
7. Forecast scores and EV must report primary and fallback segments separately.

This prevents the 100% object policy coverage from becoming look-ahead-biased market coverage.

## Interpretation and remaining limits

KORD has strong operational history for the tested year: 364 primary runs plus one verified
fallback. This is sufficient to retain NBM as the Chicago probabilistic baseline candidate.

It is not yet a final source `PASS` because:

- retrospective object Last-Modified is only a publication proxy, not independently measured
  historical first-seen time;
- the NBM MaxT 18-hour window still needs exact Chicago local-day semantic reconciliation;
- one 365-day window does not establish older-year daily missingness or every model regime; and
- NBM does not solve forecast coverage for the ten retained non-US cities.

## Next smallest experiment

Begin global-provider feasibility with ECMWF Open Data: retrieve actual deterministic/ensemble
objects and inventories, measure rolling retention and licensing, verify temperature variables and
determine whether historical as-issued depth can support the retained international cities.
