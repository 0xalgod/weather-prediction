# EXP-20260907-us-nbm-local-day-semantics-v1

## Status

`PASSED` — 44 locked city-date windows evaluated on 2026-09-07.

## Hypothesis

Across all 11 US cities, prior-day 07Z NBM f41 probabilistic MaxT is not a resolution-equivalent local-calendar-day label. Its documented daytime window should nevertheless overlap at least 16 hours of each tested market day, so it may remain only as an explicitly labelled predictive proxy.

## Data and method

Use the frozen 1,918-event US inventory to confirm city/station identities. Evaluate standard time, the 2026 spring DST transition, daylight time, and the 2026 fall DST transition using IANA timezones. Define the market window as local midnight through the next local midnight. Compare it with the NBM MaxT window locked from existing official-product evidence as target-date 12:00 UTC through next-day 06:00 UTC (18 hours), reported at target+24h.

## Gates

Require exactly 11 cities and 44 city-date rows; no timezone or station-resolution mismatch; minimum overlap 16 hours; maximum NBM time outside the market day two hours; and zero exact-window equivalences. Passing permits only `PROXY_18H_MAX`, with overlap and omitted/outside hours retained per row.

## Boundary

No outcome, price, forecast value, model score, EV, P&L, or order is used. Passing does not mean that NBM directly predicts the resolution label; forecast skill must be measured later against actual outcomes.

## Result

All 11 cities and 44 city-date rows passed identity and timezone checks. The NBM window overlapped 16–18 hours of the market-local day, omitted at most eight market hours, and extended at most two hours outside it. Spring/fall DST days were correctly represented as 23/25-hour market days. No window was exactly equivalent.

Decision: retain f41 only as `PROXY_18H_MAX`, with timezone, DST, overlap, missing-hour, and outside-hour metadata. It must not be used as the outcome label. A bounded, stratified US dataset pilot may now measure whether the proxy adds predictive value against actual resolved outcomes and market probabilities.
