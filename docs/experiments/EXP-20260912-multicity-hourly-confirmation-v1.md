# EXP-20260912-multicity-hourly-confirmation-v1

## Status

`PASSED` — corrective data V2 passed and every preregistered confirmation gate passed in the single scoring run.

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

## Data-quality V1 result

KJFK, KLAX, KDFW, and KMIA passed every gate. KSEA failed the zero-out-of-range-temperature gate on one 2024-12-26 02:53 LST row. NOAA's structured field says 80.0°C and associated relative humidity says 2%, while the same raw row's METAR says `09/05`. No model was scored and no confirmation outcome was inspected.

The V1 failure remains recorded. A separate, preregistered V2 may treat physically invalid temperature and its dependent relative humidity as missing, without manually substituting the METAR temperature, and must rerun every station-level gate.

## Confirmation result

The frozen procedure scored 1,773 eligible station-days. Pooled expanding-Ridge MAE was 2.032°C versus persistence MAE 2.350°C, a 13.56% improvement; pooled bias was -0.136°C. Every station had positive MAE skill, ranging from 9.42% at KLAX to 18.17% at KMIA, and every station remained within 1°C absolute bias.

The target-date-cluster bootstrap paired MAE reduction was 0.319°C with 95% interval [0.236, 0.401] across 359 date clusters. Every confirmation gate passed. Decision: `CONFIRMATION_PASS`.

The confirmed claim is limited to next-day point forecasting from prior-day local observations. Probability calibration and market incremental value remain untested.
