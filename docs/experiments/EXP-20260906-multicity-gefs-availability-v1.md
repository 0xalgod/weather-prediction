# EXP-20260906 Multi-city GEFS Availability v1

## Status

`PASSED` — the locked 92-event inventory completed on 2026-09-06.

Implementation provenance amendment before retrieval: the frozen selected-event manifest is an explicit input for `endDate`; no cohort rule, metric, threshold, or forecast value changed.

## Question

For the 46-city station-mapped cohort, are prior-day 00Z NOAA GEFS aggregate mean and spread TMAX objects present and published early enough to construct time-correct forecast features at the market horizons?

## Locked forecast contract

For each event, resolve the official coordinate to an IANA timezone using the frozen 2026c timezone polygons. Use the 00Z GEFS run on the calendar day before the target local date. Require both `geavg` and `gespr`, plus data and index objects, at every canonical six-hour TMAX step that overlaps the station-local calendar day.

Publication admissibility is horizon-specific: the later `LastModified` timestamp of each data/index pair must be no later than `event endDate - horizon`. The evaluated horizons are 6, 12, 18, 24, and 36 hours.

## Primary gate

The 18-hour horizon passes if at least 90% of 92 events and at least 40 cities have every required pair present and publication-admissible. Timezone failures must be zero, duplicate events zero, and listing request errors at most 2%.

Prior KORD evidence showed continuous archive availability, but multi-city local-day step requirements and horizon publication coverage are unknown.

## Boundary

This is metadata inventory only; forecast values are not downloaded. `geavg`/`gespr` provide ensemble aggregate features, not a full member distribution. Overlapping six-hour blocks can include hours outside the local day and must retain that contamination metric. Passing does not establish forecast accuracy, market edge, executable EV, or P&L.

## Result

All 40 unique GEFS run-date listings succeeded, with zero timezone or duplicate-event failures. Every one of the 92 events across 46 cities had all required `geavg`/`gespr` data-index pairs.

| Hours before event end | Complete and published events | Rate | Cities |
|---:|---:|---:|---:|
| 6 | 92/92 | 100% | 46 |
| 12 | 92/92 | 100% | 46 |
| 18 | 92/92 | 100% | 46 |
| 24 | 92/92 | 100% | 46 |
| 36 | 0/92 | 0% | 0 |

The 36-hour failure is entirely publication timing: objects existed but all were published after that cutoff. The primary 18-hour gate passed at 100%.

Only 6/92 events have an exact four-block local-day partition. The remaining 86 use five overlapping blocks and include six hours outside the local day. Both the overlap proxy and contamination indicator must be retained; they cannot be labeled resolution-equivalent.

## Decision

Use the 18-hour horizon as the primary model-vs-market pilot because both market-price and GEFS coverage exist there. Keep 6/12/24 hours as secondary horizons and exclude 36-hour GEFS from this feature contract.
