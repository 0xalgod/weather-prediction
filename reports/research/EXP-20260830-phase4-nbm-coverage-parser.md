# EXP-20260830 Phase 4 — NBM archive coverage and KORD value parser

**Status:** `PASSED` for sampled coverage/parser contract; NBM source remains `CONDITIONAL_PASS`  
**Data cut-off:** 2026-08-30T19:39Z  
**Scope:** Public AWS NBP 01Z, KORD, 2023-08 through 2026-08

## Pre-registered questions

1. Are NBP 01Z objects present across a deterministic monthly grid and around documented model
   upgrade dates, rather than only at two convenient endpoints?
2. Can immutable KORD bulletin bytes be transformed into explicit model-run, forecast-hour,
   valid-time, mean, standard-deviation and percentile records without losing provenance?

A sampled coverage success does not imply daily continuity. Every missing object remains an
explicit missing-run observation.

## Coverage design

- First calendar day of every month from 2023-08 through 2026-08: 37 dates.
- Dates immediately before/on/after the registered v4.2, v4.3, v5.0 and 2026 temperature-update
  boundaries: 12 dates.
- Duplicate dates retained once, producing 49 unique object checks.
- Exact product key: `run_date + 01Z + NBP text`.
- Evidence: public-object HTTP status, content length, ETag, Last-Modified, observation UTC and local
  request latency.

The check is metadata-level for the 47 additional dates. The two endpoint files remain the
fully-downloaded/checksummed content samples.

## Coverage results

| Metric | Result |
|---|---:|
| Unique sampled dates | 49 |
| HTTP 200 | 48 |
| Sample coverage | 97.959% |
| Monthly samples | 37 |
| Boundary samples | 12 |
| Boundary failures | 0 |
| Median/maximum HEAD latency | 0.624 / 1.102 s |
| Mean available object size | 34,796,159 bytes |

The sole missing object was `2026-06-01 01Z` (`HTTP 404`). Targeted follow-up showed:

- 2026-05-30, 2026-05-31, 2026-06-02 and 2026-06-03 01Z: available;
- 2026-06-01 00Z, 07Z, 13Z and 19Z: available; and
- 2026-06-01 01Z: missing.

This is a cycle-level hole, not evidence of a missing day or broad archive outage. It also proves
that a backtest cannot assume one fixed cycle has 100% coverage or silently substitute another
cycle: any fallback changes the forecast's information time and must be explicit.

Keeping one full national 01Z bulletin per day at the observed mean size would require about 12.70
decimal GB/year before compression and filesystem overhead. A station-extracted normalized table
will be much smaller, but raw retention policy must preserve enough source bytes/checksum evidence
for audit.

## KORD parser contract and result

The parser isolates exactly one KORD NBP block and requires matching lengths for:

- forecast hour;
- QMD mean and standard deviation; and
- 10th, 25th, 50th, 75th and 90th percentiles.

It calculates `valid_time_utc = model_run_time_utc + forecast_hour`, retains only the documented
00Z-valid maximum-temperature entries, requires monotonic percentiles and carries source checksum,
HTTP Last-Modified and local ingestion time on every output row.

Actual 2023/v4.1 and 2026/v5.0 files produced:

- 9 KORD MaxT distributions per run, 18 total;
- forecast hours 23–215 for the 01Z cycle;
- zero missing values; and
- monotonic 10/25/50/75/90 percentiles in every record.

Example current first row: run `2026-08-30T01:00Z`, valid `2026-08-31T00:00Z`, mean 85°F,
SD 3°F and percentiles 81/83/85/86/88°F.

The valid timestamp is not yet the market's local-date key. The later join must apply the exact
KORD/Chicago local-day rule and verify what 18-hour MaxT window the NBM value represents; it must not
equate `valid_time_utc` to the contract date by string truncation.

## Decision

The sampled archive and parser substep passes, while NBM/KORD remains `CONDITIONAL_PASS`:

- 48/49 deterministic dates exist across 1,095 days and all model-boundary probes exist;
- actual v4.1/v5.0 bytes parse to explicit, provenance-bearing MaxT distributions; and
- a real single-cycle missing object is preserved and requires a pre-declared fallback policy.

The result is not continuous daily coverage. Historical first-publication time is still unresolved,
and station/local-day semantic reconciliation is pending.

## Next smallest experiment

Measure every day in a locked 365-day window for primary 01Z and documented alternative full cycles,
quantify primary/fallback/unavailable rates, and verify a small set of fallback files by download and
parse. Then freeze the KORD run-selection policy before any forecast scoring.
