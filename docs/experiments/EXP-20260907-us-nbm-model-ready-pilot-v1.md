# EXP-20260907-us-nbm-model-ready-pilot-v1

## Status

`PREREGISTERED` — metadata-only cohort selection has not been run.

## Hypothesis

Twenty dates shared by all 11 NBM-supported US cities can produce exactly 220 unique resolved events and a bounded, leakage-safe market/outcome/NBM join plan.

## Selection

Within 2026-01-01 through 2026-08-15, retain dates having exactly one eligible event for every locked city. Sort them, then choose 20 evenly spaced indices using `round(i*(n-1)/19)`. Selection may inspect only identity metadata; winner, price, buckets, forecast values, and scores are forbidden.

The shared-date design gives 220 events but only 20 prior-day NBM objects. Full-object transfer is capped at 800 MiB. Market request volume is measured before collection.

## Join contract and gates

Use indicative market probabilities at 18 hours before market end and prior-day 07Z NBM f41 as `PROXY_18H_MAX`. Preserve raw price vectors/sums before normalization. Require 20 dates, 220 events, 11 cities, no duplicate city-date, market-vector coverage at least 90%, NBM coverage at least 95%, final join at least 180, zero leakage, and NBM transfer no more than 800 MiB.

## Boundary

This is a staged dataset feasibility experiment. No model is fit until the join gate passes. Historical prices are not executable fills; passing cannot establish positive EV or authorize trading.
