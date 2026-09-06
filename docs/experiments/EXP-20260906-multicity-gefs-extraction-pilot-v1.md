# EXP-20260906 Multi-city GEFS Extraction Pilot v1

## Status

`PASSED` — compact extraction and decoding completed on 2026-09-06.

## Purpose

Test actual compact GRIB extraction and decoding before scaling from metadata availability to the 70-event model-ready parent cohort.

## Locked sample

The parent is the 18-hour intersection of usable complete Polymarket price vectors, admitted official station coordinates, and publication-admissible GEFS inventory: 70 events across 44 cities.

Sort parent events by longitude, latitude, target date, and event ID. Select 12 evenly spaced order-statistic indices using `round(i × (N−1) / 11)`. Selection does not inspect outcomes, prices, or forecast values and must contain at least 10 cities.

## Forecast extraction

For every selected event, download only the indexed 2 m TMAX byte range for both prior-day 00Z `geavg` and `gespr` at every six-hour block overlapping the station-local target day. Decode at the nearest GEFS grid point. Convert mean Kelvin values to Fahrenheit and spread Kelvin differences by multiplying by 9/5.

## Gates

- exactly 12 unique events and at least 10 cities;
- message success at least 98%, content errors zero, temporal leakage zero;
- coordinate delta no more than 0.36°;
- mean temperature within −100°F to 140°F and spread within 0°F to 50°F;
- observed-message transfer extrapolated to all 70 parent events below 2 GiB.

## Boundary

This pilot is not a training dataset. Aggregate mean/spread is not a full ensemble distribution, and overlapping blocks are not resolution-equivalent daily maxima. Outcomes are not used. No EV, P&L, fill, or trading claim is permitted.

## Result

The deterministic pilot selected 12 distinct cities spanning longitudes from San Francisco to Wellington. All 116 required messages were retrieved and decoded. One transient transport error recovered on retry; content errors and temporal leakage were zero.

- observed byte-range transfer: 44,778,354 bytes (42.70 MiB);
- projected 690-message parent transfer: 266,354,002 bytes (254.02 MiB), well below 2 GiB;
- maximum station-to-grid coordinate delta: 0.1669°, below 0.36°;
- `geavg` range: 45.95°F–102.47°F, median 78.17°F;
- `gespr` range: 0.36°F–3.06°F, median 1.08°F.

All locked gates passed.

## Decision

Scale compact extraction to the frozen 70-event/44-city parent cohort. Do not fit a model until the joined outcome, raw/normalized market vector, GEFS features, contamination metadata, and time checks pass their own dataset gate.
