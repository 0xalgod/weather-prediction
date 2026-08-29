# Phase 2 Resolution Registry Contract

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Date:** 2026-08-30  
**Schema version:** `0.1.0`  
**Phase status:** `IN_PROGRESS` — contract substep passed

## Question and acceptance criterion

Can the market “identity card” be represented by a versioned contract that prevents unresolved station/rule ambiguity, bucket gaps or overlaps, stale rule hashes and silent missing-data repair from entering the retained research universe?

The substep passes if a machine-readable schema exists, `RECONCILED` records require every critical field, `NO_TRADE` records preserve explicit reasons, rule text is hash-bound, discrete bucket partitions are exhaustive/non-overlapping, timestamps remain timezone-aware, and positive/negative contract tests pass.

## Contract

Each event-level registry record now binds:

- event identity, city and local market date;
- disposition plus explicit exclusion reasons;
- resolution provider, source URL, station code/name and IANA timezone;
- Celsius/Fahrenheit unit, source precision and rounding policy;
- explicit local-calendar-day observation window;
- exact rule text, SHA-256 and rule version;
- every bucket's market/condition/Yes-token/No-token identity and inclusive numeric bounds;
- Gamma and resolution retrieval timestamps/checksums plus parser version.

`RECONCILED` means every critical rule field is present and valid. A non-reconciled record may preserve missing values only with a non-empty exclusion reason and remains ineligible for research labels/trading.

## Verification

- Sanitized Fahrenheit fixture passes the complete contract.
- A bucket gap/overlap fails closed.
- A rule-text change with the old hash fails closed.
- An invalid IANA timezone fails closed.
- Missing resolution source is preserved only under an explicit `NO_TRADE` disposition.
- Repository suite: 23 tests passed.

The first test run correctly failed because the hand-written fixture hash did not match its rule text and the chosen negative timezone `EST` was available in the local zone database. The fixture was corrected to its computed SHA-256 and the negative case changed to the unambiguously invalid `Invalid/Nowhere`; the full suite then passed. No acceptance threshold changed.

## Decision

The registry contract substep passes. Phase 2 remains `IN_PROGRESS` because the contract has not yet been populated for the fixed sample, station timezones have not been independently cross-checked, and city-family rule changes have not been measured.

## Artifacts

- `schemas/resolution_registry.schema.json`
- `src/weather_quant/normalization/resolution_rules.py`
- `tests/fixtures/resolution_registry_record.json`
- `tests/test_resolution_rules.py`

## Next action

Implement the deterministic Gamma-rule/bucket parser and populate candidate registry records for all 20 sampled events, keeping the eight Phase 1 exclusions as explicit `NO_TRADE` records.
