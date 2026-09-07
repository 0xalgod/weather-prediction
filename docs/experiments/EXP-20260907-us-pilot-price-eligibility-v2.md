# EXP-20260907-us-pilot-price-eligibility-v2

## Status

`PREREGISTERED` — post-hoc corrective reclassification has not been run.

## Disclosure and hypothesis

The original 90% coverage gate failed at 85%. This corrective design was created after seeing that result and cannot supersede it. The hypothesis is that, without replacing dates or events, the real-time observable rule “complete vector and no more than 12 hours stale” can define `PRICE_ELIGIBLE`; all other rows remain recorded as `NO_TRADE`.

## Locked gates

Require at least 180 eligible events, 15 eligible target-date clusters, 15 eligible events per city, all 11 cities, and zero request errors, leakage, or duplicate events. The cohort, dates, 18-hour cutoff, and 12-hour staleness threshold cannot change.

Passing permits NBM dataset construction for the frozen cohort, with scoring restricted by the same observable eligibility rule. It does not convert the original price gate to a pass and is not evidence of model skill or EV.
