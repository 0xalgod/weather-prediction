# Phase 2 Candidate Resolution Registry Population

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Date:** 2026-08-30  
**Registry schema/parser:** `0.1.0`  
**Input:** Fixed 20-event Phase 1 reconciliation sample  
**Status:** Candidate population substep passed; station/timezone verification pending

## Pre-registered question

Can the fixed sample be converted deterministically into the versioned registry contract without silently promoting Phase 1 exclusions or unverified station metadata into backtest-ready labels?

Acceptance required exactly 20 records, stable byte-for-byte output, preserved Phase 1 dispositions, parsed rule hashes and numeric bucket partitions where identifiers exist, and zero schema/semantic validation failures.

## Result

| Measure | Result |
|---|---:|
| Registry records | 20 |
| Structurally valid station-unverified candidates | 12 |
| Hard `NO_TRADE` records | 8 |
| Parsed bucket records | 161 |
| Candidate-record buckets | 128 |
| Distinct station codes represented | 16 |
| Celsius / Fahrenheit / unknown-rule records | 15 / 2 / 3 |
| Distinct exact rule hashes | 20 |

All 12 Phase 1 retained events produced complete event/market/condition/token chains, numeric inclusive bucket partitions, exact rule hashes, local dates, station codes and proposed IANA timezones. They remain `CANDIDATE_STATION_UNVERIFIED`, with exclusion reason `STATION_TIMEZONE_UNVERIFIED`; they are not yet permitted as backtest/trading labels.

The eight Phase 1 exclusions were preserved:

- 3 `NO_TRADE_MISSING_RESOLUTION_SOURCE`;
- 3 `NO_TRADE_NON_TERMINAL_OR_CANCELLED`;
- 2 `NO_TRADE_OUTCOME_SOURCE_MISMATCH`.

The two identifier-incomplete events could not produce bucket identity rows and retain `INCOMPLETE_BUCKET_IDENTIFIERS` alongside their non-terminal exclusion. No missing identifier was fabricated.

## Determinism and tests

- A second run to a new path matched the committed JSONL byte-for-byte.
- Candidate records run the same rule-hash, timezone, provenance and bucket-partition validations as final records.
- Invalid station candidates remain excluded even when structurally complete.
- Repository suite: 26 tests passed.

## Decision

The parser/population substep passes. Candidate timezones are isolated in `configs/station_timezone_candidates.json` and explicitly marked `UNVERIFIED_CANDIDATE`. Phase 2 remains `IN_PROGRESS`; no candidate may be promoted to final `RECONCILED` until station identity and timezone are checked against authoritative metadata.

## Artifacts

- `reports/data_quality/EXP-20260830-phase2-resolution-registry-candidate.jsonl`
- `configs/station_timezone_candidates.json`
- `scripts/build_resolution_registry.py`
- `src/weather_quant/normalization/resolution_rules.py`

## Next action

Independently verify station identity and IANA timezone for the 12 candidate records, record primary-source evidence, and promote only verified records to final `RECONCILED` registry status.
