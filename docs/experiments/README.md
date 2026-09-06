# Experiment Index

This index is the project-level directory of material research experiments. Detailed evidence and phase history live in each experiment's `PLAN.md`.

| Experiment ID | Title | Status | Started | Completed | Primary decision | Plan |
|---|---|---|---|---|---|---|
| EXP-20260830-data-source-feasibility | Point-in-time market and weather data feasibility | `IN_PROGRESS` | 2026-08-30 | — | Phase 5: event 946566 adapter ready; wait for bounded Sep 4 trigger window | [PLAN.md](EXP-20260830-data-source-feasibility/PLAN.md) |
| EXP-20260903-chicago-vertical-slice | One-event KORD forecast-to-executable-price EV mechanics | `PASSED` | 2026-09-03 | 2026-09-03 | Mechanics passed; no edge/trade claim | [PLAN.md](EXP-20260903-chicago-vertical-slice/PLAN.md) |
| EXP-20260903-chicago-paper-cohort | Fixed-time KORD prospective paper pilot | `IN_PROGRESS` | 2026-09-03 | — | Day 1/14 captured; Gaussian no-trade, quantile paper-trade; outcome pending | [PLAN.md](EXP-20260903-chicago-paper-cohort/PLAN.md) |
| EXP-20260903-chicago-historical-price-coverage | Deterministic closed Chicago CLOB price-history coverage | `PASSED` | 2026-09-03 | 2026-09-03 | 30/30 events and 330/330 tokens covered; sparse indicative prices only | [PLAN.md](EXP-20260903-chicago-historical-price-coverage/PLAN.md) |
| EXP-20260906-multicity-price-horizon-pilot-v1 | 48-city indicative price-vector horizon coverage | `PASSED` | 2026-09-06 | 2026-09-06 | 96 events; usable vectors 56.25%–75%; all 48 cities represented | [report](EXP-20260906-multicity-price-horizon-pilot-v1.md) |
| EXP-20260906-multicity-station-mapping-v1 | 48-city station coordinate mapping | `FAILED` | 2026-09-06 | 2026-09-06 | Small metadata snapshot mapped only 22/96 events and 11 cities | [report](EXP-20260906-multicity-station-mapping-v1.md) |
| EXP-20260906-multicity-station-mapping-v2 | Official ISD corrective station mapping | `PASSED` | 2026-09-06 | 2026-09-06 | 92/96 events and 46 cities mapped; known mismatch admission zero | [report](EXP-20260906-multicity-station-mapping-v2.md) |
| EXP-20260906-multicity-gefs-availability-v1 | Prior-day GEFS aggregate horizon availability | `PASSED` | 2026-09-06 | 2026-09-06 | 92/92 events at 6–24h; 0/92 at 36h due publication timing | [report](EXP-20260906-multicity-gefs-availability-v1.md) |
| EXP-20260906-multicity-gefs-extraction-pilot-v1 | Global compact GEFS decode and cost pilot | `PASSED` | 2026-09-06 | 2026-09-06 | 116/116 messages; 44.8 MB observed, 266 MB parent projection | [report](EXP-20260906-multicity-gefs-extraction-pilot-v1.md) |
| EXP-20260906-multicity-gefs-full-ingestion-v1 | Full 70-event/44-city GEFS input layer | `PASSED` | 2026-09-06 | 2026-09-06 | 690/690 compact messages; 248.1 MB; leakage/content errors zero | [report](EXP-20260906-multicity-gefs-full-ingestion-v1.md) |
| EXP-20260906-multicity-model-ready-v1 | 18h outcome/market/GEFS model-ready join | `PASSED` | 2026-09-06 | 2026-09-06 | 70/70 events, 44 cities; all identity/time/data gates passed | [report](EXP-20260906-multicity-model-ready-v1.md) |
| EXP-20260907-multicity-fixed-benchmark-v1 | Fixed market/GEFS chronological benchmark | `FAILED` | 2026-09-07 | 2026-09-07 | Blend worsened test log loss 36.6%; clustered CI wholly adverse | [report](EXP-20260907-multicity-fixed-benchmark-v1.md) |
| EXP-20260903-chicago-historical-join | Locked Chicago forecast/outcome join | `PASSED` | 2026-09-03 | 2026-09-04 | 30/30 NBM/outcome joins; scoring dataset unlocked | [PLAN.md](EXP-20260903-chicago-historical-join/PLAN.md) |
| EXP-20260904-chicago-baseline-scoring | Fixed Gaussian/quantile/uniform scoring on 30 Chicago dates | `PASSED` | 2026-09-04 | 2026-09-04 | NBM beats uniform; market point-in-time coverage 0/30 | [PLAN.md](EXP-20260904-chicago-baseline-scoring/PLAN.md) |
| EXP-20260904-chicago-walkforward-calibration | Expanding-window NBM proxy calibration on 114 Chicago dates | `FAILED` | 2026-09-04 | 2026-09-04 | 112 eligible; version/leakage gates failed; no training | [PLAN.md](EXP-20260904-chicago-walkforward-calibration/PLAN.md) |
| EXP-20260904-chicago-walkforward-calibration-v2 | Post-hoc corrective expanding-window calibration | `FAILED` | 2026-09-04 | 2026-09-05 | Shift/spread calibration failed; raw quantile retained | [PLAN.md](EXP-20260904-chicago-walkforward-calibration-v2/PLAN.md) |


## Status policy

Status values and lifecycle rules are defined in [`docs/agents.md`](../agents.md). Update this index in the same commit as every experiment-level status transition.
