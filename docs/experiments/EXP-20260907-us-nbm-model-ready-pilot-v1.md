# EXP-20260907-us-nbm-model-ready-pilot-v1

## Status

`IN_PROGRESS` — metadata selection passed; market/NBM collection and join remain.

## Hypothesis

Twenty dates shared by all 11 NBM-supported US cities can produce exactly 220 unique resolved events and a bounded, leakage-safe market/outcome/NBM join plan.

## Selection

Within 2026-01-01 through 2026-08-15, retain dates having exactly one eligible event for every locked city. Sort them, then choose 20 evenly spaced indices using `round(i*(n-1)/19)`. Selection may inspect only identity metadata; winner, price, buckets, forecast values, and scores are forbidden.

The shared-date design gives 220 events but only 20 prior-day NBM objects. Full-object transfer is capped at 800 MiB. Market request volume is measured before collection.

Pre-data amendment: after event IDs are frozen, market request count is the selected events' bucket-count sum. Conservative NBM transfer is 20 times the largest full-object byte count in the locked three-date station probe.

Pre-retrieval amendment: query the Polymarket CLOB `prices-history` endpoint with `interval=all`, one-minute fidelity, 30-second timeout, at most three attempts, and linear one-second retry backoff. At the locked 18-hour cutoff, select only the latest point at or before cutoff and require maximum staleness of 12 hours for a usable full vector.

## Join contract and gates

Use indicative market probabilities at 18 hours before market end and prior-day 07Z NBM f41 as `PROXY_18H_MAX`. Preserve raw price vectors/sums before normalization. Require 20 dates, 220 events, 11 cities, no duplicate city-date, market-vector coverage at least 90%, NBM coverage at least 95%, final join at least 180, zero leakage, and NBM transfer no more than 800 MiB.

## Boundary

This is a staged dataset feasibility experiment. No model is fit until the join gate passes. Historical prices are not executable fills; passing cannot establish positive EV or authorize trading.

## Stage 1 result — selection and cost

The frozen metadata-only rule found 138 full-city dates and selected 20 dates spanning 2026-03-24 through 2026-08-15. The cohort contains exactly 220 unique events, 20 per city, with zero duplicate city-date rows.

The next stage requires 2,420 YES-token price-history requests. Twenty NBM objects have a conservative projected transfer of 696,133,480 bytes (about 664 MiB), below the locked 800 MiB ceiling. Stage 1 passed; no forecast or price value was used in selection.
