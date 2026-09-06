# EXP-20260906 Multi-city Model-ready Dataset v1

## Status

`PREREGISTERED` — event-level feature/outcome join has not been run.

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
