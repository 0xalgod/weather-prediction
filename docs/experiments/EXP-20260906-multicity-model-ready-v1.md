# EXP-20260906 Multi-city Model-ready Dataset v1

## Status

`PASSED` — the locked event-level join completed on 2026-09-06.

Pre-join provenance amendment: the frozen GEFS horizon artifact is an explicit source for `exact_partition`, `outside_local_seconds`, expected message count, and cutoff. No cohort, feature formula, gate, or observed value changed.

## Cohort

The cohort is frozen upstream: 70 events across 44 cities at the 18-hour horizon, each with a complete and sufficiently fresh indicative Polymarket vector, an admitted station coordinate, and complete publication-admissible GEFS messages.

## Join contract

One row per event contains:

- exactly one terminal winning bucket;
- raw bucket YES prices, raw cross-bucket sum, and normalized categorical probabilities;
- native-unit ordered bucket bounds and continuity-corrected Fahrenheit thresholds;
- maximum overlapping-block GEFS mean, spread at that same peak step, and maximum block spread;
- exact-versus-overlap local-day semantics and outside-local seconds;
- all source identity and time provenance required to recheck leakage.

Peak-step ties use the lowest forecast step. Celsius bucket thresholds are continuity-corrected by ±0.5°C before conversion to Fahrenheit; Fahrenheit buckets use ±0.5°F. Open tails remain open.

## Gates

Require exactly 70 unique events and 44 cities, complete fields, finite numeric values, one winner per event, normalized probability error at most 1e-9, exact expected forecast message counts, and zero temporal leakage.

## Boundary

This dataset gate precedes all model fitting. Market prices are indicative, not fills; GEFS overlap is a proxy, not resolution-equivalent. Passing does not demonstrate forecast skill, edge, executable EV, or P&L.

## Result

All 70 candidate events joined successfully across 44 cities. Exclusions, duplicates, missing required fields, nonfinite values, temporal leakage, winner anomalies, and forecast message-count mismatches were all zero. Maximum market normalization error was `1.11e-16`.

The dataset spans 2026-03-28 through 2026-08-21. It contains 54 Celsius and 16 Fahrenheit events; every event has 11 ordered buckets. Twenty-six cities have two events and 18 have one. Seven outcomes landed in a tail bucket. Raw market sums range from 0.9615 to 1.113, with median 1.033.

Only five events are exact local-day partitions; 65 are explicitly marked overlap proxies.

## Decision

The data-quality gate passed. The sample is nevertheless small and sparse by city, so the first evaluation must compare fixed, transparent global baselines under a chronological split. High-capacity or city-specific training is not justified.
