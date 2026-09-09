# EXP-20260909-us-nbm-13z-coverage-v1

## Status

`PASSED` — timing and content probe completed on 2026-09-09.

## Hypothesis

Prior-day 13Z NBM should be published before the 18-hour market cutoff at prior-day 18:00 UTC and provide f35 MaxT mean, standard deviation, and P10/P25/P50/P75/P90 for all 12 US station regimes. It is six hours fresher than the rejected 07Z f41 input.

## Probe and gates

Download one full 13Z object for target dates January 15, May 15, and August 15, 2026. Extract 12 stations using exact-only duplicate canonicalization. Require 36/36 complete f35 feature rows, all HTTP Last-Modified timestamps at or before the locked cutoff, no conflicting duplicate, and at most 120 MiB total transfer.

Passing establishes only timing and content feasibility. Any model comparison must use a newly selected date cohort disjoint from prior validation/test; this probe cannot reopen or rescore those outcomes.

## Result

All three 13Z objects downloaded and all 36/36 station-date f35 records contained complete probabilistic fields. Every HTTP Last-Modified timestamp preceded the prior-day 18:00 UTC cutoff. Retrieval failures, station errors, and conflicting duplicates were zero. Total transfer was 104,224,895 bytes, below 120 MiB.

The six-hour fresher 13Z candidate is operationally feasible. Predictive comparison remains untested and must use dates disjoint from all prior development, validation, and test dates.
