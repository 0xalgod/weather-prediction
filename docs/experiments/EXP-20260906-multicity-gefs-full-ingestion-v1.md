# EXP-20260906 Multi-city GEFS Full Ingestion v1

## Status

`PASSED` — the full compact ingestion completed on 2026-09-06.

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

## Result

All 690 expected messages across 70 events and 44 cities were retrieved and decoded. Seven transient transport errors recovered on retry; terminal content errors and temporal leakage were zero.

- total compact transfer: 248,128,443 bytes (236.63 MiB);
- 345 mean and 345 spread messages;
- mean range 38.75°F–105.89°F, median 77.09°F;
- spread range 0.18°F–5.22°F, median 1.26°F;
- maximum station-grid coordinate delta 0.1669°;
- 5 exact-partition events used 8 messages; 65 overlap-proxy events used 10.

Every locked gate passed. The immutable raw result carries the legacy runner label `GEFS_EXTRACTION_PILOT_PASS`; this is a naming defect only. The tracked report records the correct decision `GEFS_FULL_INGESTION_PASS`, and the runner has been corrected for future executions without rewriting raw data.

## Decision

Freeze this forecast input layer and proceed to the event-level model-ready join. No model fitting is authorized until winner identity, market normalization, forecast aggregation, missingness, duplicates, and temporal checks pass.
