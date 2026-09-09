# EXP-20260909-us-24h-price-coverage-v1

## Status

`FAILED` — only 35% of events were eligible at 24 hours.

## Hypothesis and method

At 24 hours before market end, the already downloaded histories and prior-day 07Z NBM publications leave a balanced sample large enough for an earlier-horizon model experiment. No network request is allowed.

For every frozen event and bucket, select the latest valid price point at or before the 24-hour cutoff and require no more than 12 hours staleness. A full vector requires every bucket. Require the NBM object's HTTP Last-Modified timestamp at or before the same cutoff. Ineligible events remain explicit `NO_TRADE` rows.

## Gates

From all 220 events, require at least 165 eligible events (75%), 15 target-date clusters, 15 eligible events per city, all 11 cities, and zero price leakage, late NBM publication, or duplicate events. These thresholds ensure a balanced sample comparable in minimum size to the 18-hour pilot while recognizing earlier-horizon liquidity risk.

Passing permits only a new preregistered 24-hour model benchmark. This is a disclosed additional-horizon hypothesis; it does not rescue the failed 18-hour model or establish executable EV.

## Result

Only 77/220 events (35%) were eligible, versus the required 165/75%. The sample retained seven target-date clusters and seven events per city, versus the required 15 each. All 11 cities remained represented, with zero duplicate events, post-cutoff price leakage, or NBM publications after cutoff.

The failure is early market-vector availability, not forecast publication. The 24-hour modeling path is rejected. Additional arbitrary price horizons will not be searched on this cohort.
