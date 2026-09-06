# EXP-20260907 US NBM Station Coverage v1

## Status

`FAILED` — strict coverage was 35/36 on 2026-09-07.

## Pivot rationale

Global aggregate GEFS failed both fixed and calibrated incremental benchmarks. The full resolved inventory contains a substantially larger station-level US opportunity: 1,918 events across 11 cities and 12 station regimes. Denver changes between KBKF and KDEN; all other cities have one observed ICAO regime.

## Probe

On 2026-01-15, 2026-05-15, and 2026-08-15 target dates, inspect the prior-day 07Z NBM probabilistic text for all 12 stations. Require exactly one forecast-hour-41 MaxT record with mean, standard deviation, and P10/P25/P50/P75/P90. Dates and stations were selected without outcomes, prices, or forecast values.

Every station-date block and required field must be present, with zero duplicates and temporal leakage. This strict gate determines whether a ≥200-event US price/forecast pilot is worth building.

## Boundary

This checks station/product content only. NBM daytime MaxT semantics across US timezones require a separate review before resolution equivalence is claimed. No model, accuracy, EV, P&L, or trading claim is permitted.

## Result

All three full NBM objects were publication-admissible and transferred 104,244,121 bytes. Thirty-five of 36 station-date rows parsed with complete fields and zero temporal leakage. Twelve passed rows were NBM v4.3 and 23 were v5.0.

KDEN on 2026-05-15 failed because its v5.0 header occurs twice at byte offsets 14,960,801 and 14,964,485. Initial inspection shows identical prefixes, but v1 correctly rejected duplicate occurrence without assuming equality. The strict 100% gate failed.

Thresholds will not change. A corrective v2 may admit the row only if it proves the two complete station blocks are byte-identical; conflicting duplicates remain a hard failure.
