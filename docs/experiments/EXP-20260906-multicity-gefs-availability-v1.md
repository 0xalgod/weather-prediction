# EXP-20260906 Multi-city GEFS Availability v1

## Status

`PREREGISTERED` — no 92-event GEFS inventory has been retrieved.

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
