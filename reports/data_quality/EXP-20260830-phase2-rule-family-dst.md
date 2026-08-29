# Phase 2 City-Family Revisions and DST Boundary Validation

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Date:** 2026-08-30  
**Closed-history input:** 8,222 events, 54 city labels  
**Phase decision:** `PASSED` for the registered retained-sample gate

## Question and gate

Can the registry safely avoid static city-level station/rule assumptions, and can local calendar days be converted to UTC without DST leakage or off-by-one-day errors?

Phase 2 exit required at least 3 cities with exact source/station/window/unit mappings and 100% critical-field completeness among retained sample records. Full-history parsing coverage and regime changes were measured as secondary integrity diagnostics; incomplete records remain excluded.

## Corrected full-history results

| Measure | Result |
|---|---:|
| Closed events | 8,222 |
| City labels | 54 |
| Complete station+unit rule parses | 7,321 (89.0416%) |
| Incomplete parses | 901 (10.9584%) |
| Missing station/source | 639 |
| Station known but unit/rule wording unparsed | 262 |
| Cities with more than one station code | 2 |
| Cities with more than one temperature unit | 0 |
| Cities with more than one canonical rule template | 52 |

Detected station transitions:

- Denver: `KDEN → KBKF`, first observed at event `306357`, end date 2026-03-29.
- Paris: `LFPG → LFPB`, first observed at event `387419`, end date 2026-04-19.

The first analysis attempt incorrectly reported 46 multi-station cities because NWS URLs such as `https://www.weather.gov/wrh/timeseries?site=kord` were parsed using their path tail (`timeseries`) rather than the `site` query parameter. That output was invalidated before commit. The corrected parser extracts `site`, uppercases the ICAO code and is protected by a regression test; the rerun reduced the count from 46 to 2.

Fifty-two cities have multiple date-normalized rule templates. Therefore a city-level static rule is unsafe even where the station does not change. Exact rule hashes and event-effective versions remain mandatory.

## DST/local-day checks

The local-day helper constructs `[local midnight, next local midnight)` and converts both boundaries independently to UTC using the event's IANA zone. Tests confirm:

- Toronto 2026-03-08 spring transition: 23-hour UTC window.
- Toronto 2026-11-01 fall transition: 25-hour UTC window.
- Kuala Lumpur on the same calendar date: 24-hour window.

This prevents the common error of adding a fixed 24 hours in UTC and assigning observations to the wrong local market day.

## Phase 2 decision

Phase 2 passes its pre-registered exit gate:

- 11 final `RECONCILED` records across 11 cities exceed the ≥3-city minimum.
- Critical registry fields are complete for 100% of those retained records.
- Bucket partitions, rule hashes, station/timezone evidence and local-day semantics are validated.
- Every non-retained record has an explicit exclusion disposition.

The pass applies to the verified registry, not all 8,222 historical events. The 901 incomplete full-history parses are not labels and cannot enter training/backtests. Future scale-up requires parser support and reconciliation for each new rule/provider regime.

## Artifacts

- `reports/data_quality/EXP-20260830-phase2-rule-family-revisions.json`
- `src/weather_quant/normalization/resolution_rules.py`
- `src/weather_quant/normalization/manual_reconciliation.py`
- 31 repository tests pass.

## Next action

Begin Phase 3 by defining the point-in-time executable order-book snapshot contract and testing public CLOB REST coverage without authenticated calls or live orders.
