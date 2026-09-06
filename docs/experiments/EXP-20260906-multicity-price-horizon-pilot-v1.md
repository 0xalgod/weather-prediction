# EXP-20260906 Multi-city Price Horizon Pilot v1

## Status

`PREREGISTERED` — price-history retrieval has not started.

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
