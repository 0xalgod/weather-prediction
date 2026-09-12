# EXP-20260912-multicity-hourly-confirmation-v1

## Status

`PREREGISTERED` — no hourly values or outcomes from the five confirmation stations have been retrieved or scored.

## Hypothesis

The frozen KORD daily expanding Ridge alpha-100 procedure generalizes across five prespecified unseen climate regimes. It must improve pooled MAE versus persistence by at least 5%, maintain pooled absolute bias at or below 1°C, and produce a strictly positive lower endpoint of the 95% target-date-cluster-bootstrap interval for paired MAE reduction.

## Frozen cohort

| City | ICAO | GHCN ID | Role |
|---|---|---|---|
| New York | KJFK | USW00094789 | Unseen confirmation |
| Los Angeles | KLAX | USW00023174 | Unseen confirmation |
| Dallas | KDFW | USW00003927 | Unseen confirmation |
| Miami | KMIA | USW00012839 | Unseen confirmation |
| Seattle | KSEA | USW00024233 | Unseen confirmation |

Stations were selected for climate diversity and major-airport continuity, not observed performance. None may be removed after retrieval. Chicago/KORD is excluded because it was used to develop the candidate.

## Protocol and gates

- Retrieve immutable NOAA LCDv2 annual objects for 2024–2026 and build 2024-08-01–2026-07-31 station panels.
- Stop before scoring unless every station has at least 99% SOD-label coverage, at least 95% cutoff-window coverage, no station-ID mismatch, no duplicate SOD date, and no out-of-range temperature.
- Use the first 365 target dates as initial station-specific history and the next 365 calendar dates as confirmation evaluation.
- Preserve the 18:00 LST cutoff, 18-hour eligibility rule, same 48 features, Ridge alpha 100, and daily expanding fit. No tuning or station pooling is allowed.
- Require all pooled statistical gates, at least four stations with positive MAE improvement, and at least three stations meeting both 5% MAE skill and 1°C absolute bias.
- Bootstrap paired absolute-error reduction by target date across stations, 5,000 resamples, seed 20260912.

## Boundary

This confirms only next-day point-forecast generalization. It does not estimate bucket probabilities, market edge, execution, EV, P&L, or authorize orders.
