# EXP-20260906 Multi-city Station Mapping v2

## Status

`PASSED_POSTHOC_CORRECTIVE` — the locked corrective join completed on 2026-09-06.

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

## Result

Exact station parsing remained 96/96. The ISD join admitted 92/96 events (95.83%) across 46 cities, passing every locked coverage gate with zero admitted known identity contradictions.

Two Karachi events were excluded because the previously documented OPKC rule/source identity contradiction remains unresolved. Two Panama City events were excluded because MPMG lacked an admissible ISD catalog coordinate. Paris contains two explicit station regimes, LFPB and LFPG; these will not be silently pooled.

Twenty admitted events have prior manual identity review. The remaining exact ICAO joins are adequate for a gridded-forecast availability pilot, but require stronger rule-name identity review before any live city-specific strategy is promoted.

## Decision

Proceed with a 46-city, 92-event GEFS as-issued archive availability pilot. Retain the activity field as `RECENT_ACTIVITY_PROXY` and do not reinterpret it as target-date observation coverage.
