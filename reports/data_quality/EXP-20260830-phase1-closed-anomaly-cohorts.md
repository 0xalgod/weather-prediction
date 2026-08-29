# Phase 1 Closed-Market Anomaly Cohorts and Audit Sample

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Data cut-off:** 2026-08-29T21:56:35Z  
**Source run:** `data/raw/polymarket_gamma/closed=true/run=20260829T215446Z`  
**Code contract:** `closed_market_audit` schema `0.1.0`  
**Status:** Sample selected; manual reconciliation not yet performed

## Pre-registered question

Can closed-history resolution, settlement-status and identifier anomalies be separated into deterministic, overlap-aware cohorts, and can a 20-event sample be selected without discretionary cherry-picking?

Acceptance required all 8,222 source events to be classified, market-level and event-level counts to remain distinct, all known anomaly types to be represented where records exist, and exactly 20 unique events to be selected reproducibly.

## Method

All 83 immutable page envelopes were read in filename order. Each event received zero or more explicit reason codes. Market identifier completeness requires a market ID, condition ID, exactly two outcomes and exactly two CLOB token IDs. UMA status is clean only when exactly `resolved`.

Sampling uses fixed seed `EXP-20260830-phase1-manual-reconciliation-v1`. Events are ordered by SHA-256 of `seed|event_id`. The selector attempts three unique events from each of five anomaly cohorts, then five clean events, and fills any shortfall from the global hash order. Only two events contain identifier-incomplete markets, so that stratum contributes two and one hash-fill record is used.

## Results

| Measure | Count | Share of 8,222 events |
|---|---:|---:|
| Clean events | 7,470 | 90.8538% |
| Events with at least one anomaly | 752 | 9.1462% |
| Missing event resolution source | 639 | 7.7718% |
| Not automatically resolved | 116 | 1.4108% |
| Missing event close time | 57 | 0.6933% |
| Contains identifier-incomplete market | 2 | 0.0243% |
| Contains non-`resolved` UMA market | 19 | 0.2311% |

The previously reported 22 identifier-incomplete and 80 non-UMA-resolved values are **market counts**, not event counts. They are concentrated in 2 and 19 events respectively. Cohorts overlap: 54 events combine missing close time with non-automatic resolution; both identifier-incomplete events are also non-automatic and contain non-resolved UMA markets. Counts must not be summed as though cohorts were disjoint.

The selected queue has 20 unique events: five clean, three missing-source, three selected for non-automatic resolution, three for missing close time, both identifier-incomplete events, three for non-resolved UMA status, and one deterministic hash-fill clean event. Because events may carry multiple flags, the sample covers 3 missing-close-time, 11 non-automatic, 2 identifier-incomplete, 5 non-resolved UMA and 3 missing-source events.

## Quality checks

- Every raw page required a stored content SHA-256.
- Classification preserves the source page checksum on each selected event.
- The sample contains 20 unique event IDs and all five registered anomaly types.
- The full two-event identifier-incomplete population is included.
- Thirteen repository tests pass, including overlap accounting and order-independent deterministic sampling.

## Decision

The anomaly extraction and sample-selection substep passes. Gamma closed history remains suitable for manual rule/identifier reconciliation, but no sampled event is considered reconciled yet. Missing `resolutionSource` is common enough (7.77%) that parsing must define an explicit fallback or `NO_TRADE`; it cannot be silently imputed.

## Artifacts

- Machine-readable cohort counts and full queue: `reports/data_quality/EXP-20260830-phase1-closed-audit-sample.json`
- Reproduction: `PYTHONPATH=src python3 scripts/audit_closed_polymarket_markets.py --raw-directory data/raw/polymarket_gamma/closed=true/run=20260829T215446Z --output <new-output-path>`

## Next action

Manually reconcile the 20 selected events against Gamma event/market metadata and resolution-source pages, recording identifier, station/source, terminal outcome and anomaly disposition per event.
