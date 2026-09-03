# EXP-20260903-chicago-vertical-slice — Plan

## Status

`IN_PROGRESS` — pre-registered, no model/book values observed under this experiment yet.

## Research question

Can one Chicago/KORD daily-maximum market be transformed end to end from an as-issued probabilistic forecast and contemporaneous executable YES books into a complete, cost-explicit bucket EV table without temporal leakage or midpoint fills?

This is a pipeline/mechanics experiment. A positive row is not evidence of repeatable edge.

## Locked cohort

- Event: `946566`, “Highest temperature in Chicago on September 3?”
- Station/timezone: KORD / `America/Chicago`
- Resolution source: NOAA WRH KORD
- Rule SHA-256: `15ce309df35d3bb6f1f3eb7988adb87b3ff8d1fb831b775a3642f4cba75158ec`
- Identity source: `reports/data_quality/EXP-20260902-phase5-kord-upcoming-event-discovery.json`
- Identity source SHA-256: `e003e77b7f0083e4f3d1322512f8731de1f49fc4463f843c2079348cd82c7da0`
- Expected inventory: 11 mutually exclusive buckets, 11 YES tokens and 11 NO tokens.

Event selection was made before this experiment and was independent of forecast values, prices and outcome.

## Data acquisition order

1. Search backward from the most recently plausibly published NOAA NBM hourly cycle, maximum six cycles, and select the first HTTP-available probabilistic text object. Selection depends only on availability—not forecast value.
2. Parse exactly one KORD `MAXIMUM` record corresponding to the Sep 3 local maximum product valid at Sep 4 00Z. Preserve model run, published/Last-Modified, ingested time, forecast hour, raw checksum and NBM version.
3. Retrieve current public Gamma event metadata for exact bucket labels and verify event/rule/market/token identities against the locked artifact.
4. Immediately retrieve all 11 YES-token public CLOB books and per-token tick/fee metadata. Raw envelopes are immutable.
5. The interval from forecast retrieval completion to final book receipt must be no more than 15 minutes. Otherwise the run is `TEMPORAL_SKEW_FAILED` and may be rerun as a new immutable run.

Public read-only requests only. No wallet, authentication, order, outcome lookup or settlement data.

## Probability baseline

Use the NBM mean and standard deviation as a deliberately simple Gaussian baseline:

\[
T \sim \mathcal{N}(\mu_{NBM},\sigma_{NBM})
\]

Integer-temperature buckets use half-degree continuity boundaries. For inclusive `[a,b]`:

\[
q=\Phi((b+0.5-\mu)/\sigma)-\Phi((a-0.5-\mu)/\sigma)
\]

Lower and upper terminal buckets use the corresponding one-sided CDF. This assumption is not “calibrated” and must be labeled `GAUSSIAN_NBM_DIAGNOSTIC_BASELINE`. NBM p10/p25/p50/p75/p90 values are retained as diagnostics; disagreement with the Gaussian-implied quantiles is reported, not tuned away.

## Executable price and costs

- Side: buy YES only.
- Target size: `$10` notional per bucket, independently; this is a capacity probe, not a portfolio proposal.
- Price: walk asks best-first to calculate depth-weighted VWAP. Midpoint and last price are forbidden.
- Insufficient ask depth: row is `NO_EXECUTABLE_QUOTE` and no price is imputed.
- Slippage: already represented by VWAP minus best ask and reported separately.
- Fee: obtain the public per-token fee rate/schedule and preserve its source. Apply only a formula supported by primary documentation; otherwise set fee/net EV to `UNKNOWN` and do not issue `PAPER_TRADE`.
- Resolution-risk sensitivity: report gross edge and additional fixed haircuts of 1 and 2 probability points per share. These are sensitivity scenarios, not estimated costs.

For each executable row:

\[
EV_{gross}=q-p_{VWAP}
\]

Net EV is emitted only if the fee formula is verified. Every recommendation remains `DIAGNOSTIC_ONLY` in this experiment.

## Pre-registered metrics

- exact event/rule/source identity pass;
- NBM object/run/published/ingested provenance completeness;
- selected KORD target record count;
- parsed bucket count and non-overlap/exhaustiveness;
- probability sum and per-bucket range;
- successful/two-sided/one-sided/empty YES books;
- `$10` executable coverage and VWAP slippage;
- forecast-to-last-book temporal skew;
- fee provenance/formula status;
- per-bucket `q`, best bid/ask, `$10 VWAP`, gross edge, 1pp/2pp sensitivity and decision reason.

## Acceptance gate

`VERTICAL_SLICE_MECHANICS_PASS` requires all of:

- exact locked event/rule identity and 11 unique bucket/YES-token mappings;
- exactly one admissible KORD NBM target record published before book capture;
- all bucket labels parse into exhaustive, non-overlapping integer ranges;
- every probability is in `[0,1]` and sum is within `1e-9` of 1;
- forecast-to-last-book receipt skew ≤15 minutes;
- at least 9/11 buckets have sufficient asks for a `$10` buy-YES VWAP;
- no midpoint fills, identifier substitutions or imputation;
- immutable raw checksums and a reproducible output artifact;
- focused tests, full test suite and scoped Ruff pass.

Failure produces an explicit reason and a corrective experiment; thresholds will not be changed after observing values.

## Interpretation and stop rules

- This one-event slice cannot establish calibration, statistical significance, expected profitability or capital sizing.
- No `PAPER_TRADE` or live signal may be emitted, even if gross edge is positive.
- If mechanics pass, the next step is a prospective multi-day paper dataset with a predeclared minimum sample—not a more complex model.
- If fee semantics remain unresolved, gross edge is shown but net EV stays unknown.
- Settlement capture remains a parallel label-quality check and no longer blocks this mechanics experiment.

## Expected artifacts

- `configs/EXP-20260903-chicago-vertical-slice.json`
- immutable NBM, Gamma, book, tick and fee envelopes under a new run path
- `data/processed/chicago_vertical_slice/...json`
- `reports/data_quality/EXP-20260903-chicago-vertical-slice.json`
- `reports/research/EXP-20260903-chicago-vertical-slice.md`

## Update log

### 2026-09-03 — Pre-registered

- Cohort, acquisition ordering, Gaussian baseline, executable pricing, cost boundaries, metrics and gate fixed before retrieving experiment-specific forecast or price values.
- Next action: implement/test the pure bucket-probability and depth-VWAP core, then run one immutable live slice.

### 2026-09-03 — Probability and executable-price core passed

- Status remains `IN_PROGRESS`; component decision `VERTICAL_SLICE_CORE_PASS`.
- Focused 10/10, full suite 104/104 and scoped Ruff passed.
- Half-degree Gaussian bucket probability, sum-to-one, partition rejection, best-first ask VWAP, multi-level slippage and insufficient-depth behavior are now deterministic and tested.
- No live forecast/price/outcome was used in this component result.
- Next action: execute one immutable read-only NBM→event 946566→YES-book run under the pre-registered temporal and coverage gates.

## Decision log

### VSD-0001 — 2026-09-03 — Start quant mechanics before settlement sample matures

- Decision: Run a one-event, no-trade vertical slice now; keep the Sep 4 settlement capture as a parallel data-quality track.
- Evidence: Forecast and order-book primitives exist, while waiting for one settlement observation does not reduce uncertainty about the forecast-to-price join mechanics.
- Consequence: Phase 6 starts conditionally; results cannot enter backtest or trading until label and sample gates pass.

### VSD-0002 — 2026-09-03 — Use a transparent Gaussian NBM baseline

- Decision: Use NBM mean/standard deviation with half-degree bucket boundaries for the first mechanics slice.
- Alternatives: Fit a flexible distribution to five quantiles; deferred because one event cannot validate/tune it. Treat percentiles as ensemble members; rejected because they are quantiles, not exchangeable samples.
- Consequence: Output is transparent and reproducible but explicitly uncalibrated.
