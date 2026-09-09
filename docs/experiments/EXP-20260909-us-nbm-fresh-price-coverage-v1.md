# EXP-20260909-us-nbm-fresh-price-coverage-v1

## Status

`PREREGISTERED` — no network retrieval has run under this experiment.

## Hypothesis

The frozen, disjoint 10-date × 11-city cohort retains enough complete and non-stale Polymarket probability vectors at the 18-hour cutoff to support a balanced temporal comparison of prior-day 07Z and 13Z NBM forecasts.

## Data and measurement

Request the 1,210 frozen YES token histories at one-minute fidelity. For each event bucket, choose the latest valid observation at or before `end_date_utc - 18 hours`; reject a vector if any bucket is absent or if maximum staleness exceeds 12 hours. Forecast values and outcomes are forbidden inputs to this coverage decision.

## Acceptance gates

All gates must pass: exactly 110 selected events and 1,210 requests; at least 88 usable full vectors (80%); at least 8 distinct usable dates; all 11 cities represented with at least 8 usable events per city; zero terminal request errors; and zero post-cutoff points used.

The 80% balance gate is fixed before retrieval. It is slightly below the earlier cohort's observed 85% usable rate while still preserving at least eight temporal observations per city. A pass authorizes only a separately preregistered two-cycle NBM download. A failure stops forecast acquisition for this cohort.

## Boundary

Historical prices are indicative snapshots, not executable fills. This experiment cannot establish model skill, edge, net EV, P&L, or permission to send orders.
