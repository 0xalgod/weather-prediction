# EXP-20260906 Multi-city Station Mapping v2

## Status

`PREREGISTERED_POSTHOC_CORRECTIVE` — designed after v1 exposed the small metadata snapshot limitation, before joining the global ISD catalog.

## Correction

The sample, URL parser, coverage thresholds, and identity safety rule are unchanged. V2 replaces the 12-station evidence snapshot with the already downloaded official NOAA ISD station-history catalog. Exact uppercase ICAO is the only join key; city-name matching and centroid fallback remain forbidden.

When an ICAO has multiple historical records, choose maximum `END`, then maximum `BEGIN`. Coordinates must be finite and physically valid. The record must begin no later than the target date, and its last catalog activity may be at most 550 days before that target.

Because the frozen ISD catalog ends in 2025, this rule is explicitly `RECENT_ACTIVITY_PROXY`; it verifies a plausible station coordinate, not actual observation availability on the 2026 target date.

## Locked gates

- exactly 96 selected events and zero duplicates;
- station parsing at least 95%;
- coordinate admission at least 85%;
- at least 40 mapped cities;
- zero admitted ICAOs with a known identity contradiction.

## Boundary

No forecast or observation values are retrieved. Passing permits a separate GEFS availability test but does not establish forecast accuracy, resolution equivalence, EV, or executable fills.
