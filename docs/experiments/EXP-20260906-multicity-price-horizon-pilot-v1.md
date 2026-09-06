# EXP-20260906 Multi-city Price Horizon Pilot v1

## Status

`PASSED` — retrieval and locked coverage gates completed on 2026-09-06.

## Question

Can the public Polymarket price-history endpoint supply a time-correct, complete indicative probability vector across a broad city set at 6, 12, 18, 24, and 36 hours before event end?

## Hypothesis and locked sample

The frozen 48-city inventory will contribute exactly two events per city (96 total). Events are sorted by target date and event ID; one lower-median event is selected from each city's early half and one from its late half. This gives every city equal weight while spanning the observed period without inspecting price availability.

The experiment passes if:

- request error rate is at most 2%;
- at least one horizon has a full-vector event coverage rate of at least 20%;
- at least 30 of 48 cities have at least one usable full-vector event at one or more horizons;
- the selected sample has exactly 48 cities, 96 unique events, and zero duplicate event IDs.

## Time correctness

At each horizon, each YES token uses only its latest history point at or before `endDate - horizon`. Every bucket must be present and no selected point may be more than 12 hours old. Availability and staleness are reported before any cross-bucket normalization.

## Outputs

- immutable request/response envelopes per YES token;
- deterministic selected-event manifest;
- token-level validated histories;
- event × horizon coverage with raw probability sums and staleness;
- city/horizon aggregate report and gate decision.

## Interpretation boundary

Price history contains indicative timestamp-price points, not historical bid/ask depth, spread, size, side, latency, partial-fill, or fee evidence. Passing this experiment permits model-versus-market research; it does not validate executable EV or a backtest fill model. No order will be sent.

## Result

All 1,056 token requests succeeded and produced 4,381 validated history points, with zero duplicate/conflicting/out-of-window points. The deterministic sample contained exactly 96 unique events across all 48 research cities.

| Hours before end | Usable full vectors | Rate | Cities | Incomplete | Complete but stale |
|---:|---:|---:|---:|---:|---:|
| 6 | 72/96 | 75.00% | 47 | 16 | 8 |
| 12 | 72/96 | 75.00% | 45 | 19 | 5 |
| 18 | 72/96 | 75.00% | 45 | 19 | 5 |
| 24 | 60/96 | 62.50% | 39 | 35 | 1 |
| 36 | 54/96 | 56.25% | 38 | 41 | 1 |

Every city had at least one usable event at one or more horizons. All pre-registered gates passed. Twelve- and eighteen-hour rows are identical because the sparse series often supplies the same latest point at both cutoffs; this is observed availability, not independent evidence.

Median raw cross-bucket YES sums ranged from 1.0305 to 1.0475 across horizons. Consequently, scoring must retain the raw sum as a market-quality diagnostic and normalize complete positive vectors before treating them as a categorical distribution.

## Decision

Proceed to a model-ready multi-city pilot using only event-horizon rows that pass the complete-vector and staleness rule. Maintain a separate prospective order-book validation layer before making any executable EV claim.
