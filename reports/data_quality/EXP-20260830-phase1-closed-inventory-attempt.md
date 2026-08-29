# EXP-20260830 — Phase 1 closed inventory first attempt

**Data cut-off:** 2026-08-29T21:52:16Z (2026-08-30 Europe/Istanbul)
**Dataset version:** Local Gamma run `20260829T215025Z`
**Code/config version:** Pre-fix `scripts/discover_polymarket_markets.py` and discovery contract
**Covered markets:** Complete keyset traversal for `tag_slug=highest-temperature&closed=true`
**Status:** `SUPERSEDED_WITH_PARTIAL_INVALIDATION`

## 1. Objective

Measure closed highest-temperature history depth, event/market scale, storage requirements, identifier coverage, and settlement-related fields using the same keyset contract as the active inventory.

## 2. Valid run measurements

| Metric | Result |
|---|---:|
| Keyset pages | 83 |
| Source events | 8,222 |
| Duplicate event IDs | 0 |
| Unique city labels | 54 |
| Nested market rows | 89,536 |
| Earliest event end | 2025-12-30T12:00:00Z |
| Latest event end | 2026-08-29T12:00:00Z |
| Raw envelope files | 83 |
| Raw envelope disk usage | 370 MB |

These counts come from source events and nested market rows and remain valid.

The summary file checksum is:

```text
09cbabbee3092e807ddb7737312ab29ddc6fe3a039c3ba1e47eac53b5772bb45  closed-summary-20260830.json
```

## 3. Preliminary field observation

An inspected closed NYC event exposed:

- event-level `closed=true`, `automaticallyResolved=true`, `closedTime`, and a station-specific `resolutionSource`,
- market-level `closed=true`, `umaResolutionStatus=resolved`, `outcomePrices`, `conditionId`, and `clobTokenIds`,
- binary outcome prices `[0, 1]` for the inspected settled bucket.

This demonstrates that settlement-relevant fields exist in at least one record. Coverage is not yet measured across the full history.

## 4. Invalidated metrics

The first summary reported:

```text
eligible_market_count = 0
outcome_count = 0
excluded_market_count = 89,536
```

`eligible_market_count=0` is consistent with the current-book eligibility definition because every closed event end time precedes collection time.

`outcome_count=0` is invalid for historical normalization. The implementation emitted outcome-token mappings only for markets eligible for **current** book collection. This incorrectly coupled two independent concepts:

1. identifier integrity for historical analysis,
2. temporal eligibility for prospective order-book collection.

The raw envelopes, page/event/market counts, city counts and date range remain valid. Historical normalized outcome counts and identifier-complete counts must be regenerated after the contract fix.

## 5. Corrective action

The normalization contract is changed to expose both:

- `identifier_complete`: outcome/token/condition mapping is structurally valid,
- `eligible_for_book_collection`: identifier complete, order book enabled, and event temporally relevant.

Valid historical outcome-token rows are now retained even when `EVENT_END_DATE_PASSED` correctly prevents current book collection.

A new regression test requires an expired but identifier-complete market to retain both outcome-token rows while remaining ineligible for prospective book collection.

## 6. Decision

- Closed traversal itself succeeded.
- The first normalized historical outcome metric is invalidated and must not be cited.
- Phase 1 remains `IN_PROGRESS`.
- Rerun the closed inventory with the corrected contract before measuring settlement coverage or identifier integrity.

## 7. Next action

Completed. The corrected rerun is documented in `reports/data_quality/EXP-20260830-phase1-closed-inventory.md`. This file remains the append-only invalidation record for the first attempt.
