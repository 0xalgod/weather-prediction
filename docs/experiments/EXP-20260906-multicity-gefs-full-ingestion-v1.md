# EXP-20260906 Multi-city GEFS Full Ingestion v1

## Status

`PREREGISTERED` — the full 70-event cohort has not been downloaded.

## Scope

Ingest every event in the frozen 18-hour intersection: 70 events across 44 cities. The compact forecast contract is unchanged from the successful 12-city pilot: prior-day 00Z GEFS `geavg` and `gespr`, 2 m TMAX, every six-hour block overlapping the station-local target day, exact indexed byte ranges, nearest-grid decode.

No outcome or forecast value participates in cohort selection.

## Locked gates

- exactly 70 events and at least 44 cities;
- at least 98% of the expected 690 messages succeed;
- content and temporal leakage errors equal zero;
- maximum station-grid delta no more than 0.36°;
- mean temperature within −100°F to 140°F and spread within 0°F to 50°F;
- compact transfer below 2 GiB.

## Known evidence

The 12-city pilot achieved 116/116 messages, 44,778,354 bytes, zero content/leakage errors, and maximum coordinate delta 0.1669°. Full-cohort results remain unknown.

## Boundary

This produces the complete forecast input layer, not yet the joined model-ready table. Aggregate GEFS is not a full ensemble distribution, overlap windows are not resolution-equivalent, and no accuracy, EV, fill, P&L, or trading conclusion is allowed.
