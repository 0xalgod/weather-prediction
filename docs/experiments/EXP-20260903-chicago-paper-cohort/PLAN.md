# EXP-20260903-chicago-paper-cohort — Prospective pilot plan

## Status

`IN_PROGRESS` — preregistered before the first fixed-time cohort snapshot.

## Objective

Measure whether a transparent KORD probabilistic forecast produces repeatable cost-adjusted paper EV against executable Polymarket prices at a fixed decision time. The 14-day pilot tests data/model behavior and decides whether a 30+ observation study is worth continuing; it cannot prove an edge by itself.

## Locked cohort

- City/station: Chicago / KORD
- Market family: daily maximum temperature, NOAA WRH-primary rule only
- Snapshot dates: 2026-09-03 through 2026-09-16 UTC
- Target local dates: 2026-09-04 through 2026-09-17
- Decision time: 11:00 UTC daily (14:00 Europe/Istanbul), tolerance ±15 minutes
- Planned observations: 14; minimum eligible observations: 10
- Selection: exact target-date Chicago event discovered without using forecast, price or outcome values
- Missing day: preserve reason; never substitute another city/date or backfill with later prices

This requires one short foreground snapshot per day, not an always-on collector. No automatic schedule is authorized by this plan.

## Point-in-time join

For each date:

1. At 11:00 UTC ±15 minutes, find the exact active Chicago target-date event and lock event/rule/market/token identities.
2. Select the latest available NOAA NBM probabilistic-text cycle by availability-only backward search; its publication/retrieval must precede the books.
3. Select exactly one KORD maximum record valid at the product time corresponding to the target local day; record target mapping as an explicit semantic check.
4. Capture all YES books, CLOB V2 condition info and Gamma fee schedule immediately; forecast-to-last-book skew ≤15 minutes.
5. Produce Gaussian and quantile-preserving probabilities from the same as-issued forecast.
6. Calculate independent `$10` ask-depth VWAP and taker fees per bucket. Do not place an order.
7. After resolution evidence is eligible, append terminal winner and compute scores/P&L without altering the original snapshot.

## Models locked before outcomes

### Primary: NBM quantile-preserving CDF v1

Use anchors `(p,x)` = `(0.10,p10)`, `(0.25,p25)`, `(0.50,p50)`, `(0.75,p75)`, `(0.90,p90)`. Add finite tail anchors by extending the adjacent quantile slope to probabilities 0 and 1:

- lower endpoint = `p10 - max(1°F, (p25-p10) × 2/3)`;
- upper endpoint = `p90 + max(1°F, (p90-p75) × 2/3)`.

CDF values are linearly interpolated between anchors. Repeated quantile temperatures create a probability jump at that temperature; half-degree bucket boundaries avoid ambiguity for integer-resolution markets. No outcome-based smoothing or parameter fitting.

### Benchmark: Gaussian NBM v1

Use the already locked `Normal(mean, standard_deviation)` model with half-degree boundaries.

### Market reference

For scoring only, calculate a non-executable reference probability from each two-sided book midpoint and normalize across buckets. It is never used as a fill. If any bucket lacks a two-sided quote, the market-reference score for that date is missing; no imputation.

## Paper decision and execution assumptions

- Evaluate primary and Gaussian models separately; do not choose the winner post-hoc.
- Per model/date, select at most one bucket: highest `q - VWAP - fee_per_share - 0.02`.
- Emit a hypothetical paper position only if this adjusted edge is at least `0.03` per share.
- Paper stake: `$10` ask-depth purchase; no reuse of capital within a day.
- Insufficient `$10` ask depth, fee mismatch, data-quality flag or resolution uncertainty yields `NO_TRADE`.
- Maker fills/rebates are not credited in this pilot.
- No wallet, credentials, orders or live capital.

## Pre-registered metrics

Daily data quality:

- scheduled/attempted/eligible/missing snapshots and reason codes;
- rule/provider/station/target-date identity;
- forecast publication→book ordering and skew;
- bucket partition, probability sums, book-side/depth and fee reconciliation;
- Gaussian-versus-quantile total variation distance;
- maximum adjusted edge and paper/no-trade decision per model.

After eligible settlement labels:

- multiclass Brier score and log loss per model;
- market-reference score where complete;
- calibration table using preregistered broad bins `[0,.1), [.1,.25), [.25,.5), [.5,.75), [.75,1]` (descriptive only at pilot size);
- paper trades, hit rate, gross/net P&L, turnover and maximum drawdown;
- mean net EV estimate with date-cluster bootstrap 95% interval;
- concentration by bucket and top-day P&L share.

## Pilot gates

### Data gate

Pass requires at least 10/14 eligible snapshots, ≥90% bucket-level `$10` executable coverage across eligible dates, zero identity/provider mixing, zero temporal leakage and every missing/rejected row carrying a reason.

### Continue-to-30 gate

This is a resource-allocation gate, not an edge claim. Continue toward 30 eligible dates only if:

- data gate passes;
- primary quantile baseline has no unresolved semantic/calibration implementation defect;
- adjusted paper P&L is greater than `−30%` of hypothetical deployed capital;
- no single date contributes more than 50% of positive gross P&L;
- settlement-label eligibility is established for admitted outcomes.

Failing these conditions produces `STOP_OR_REDESIGN`; thresholds will not be loosened post-result. Passing produces only `CONTINUE_DATA_COLLECTION`, never `EDGE_CONFIRMED`.

### Future edge gate

No edge claim before at least 30 eligible dates. A later preregistration must require positive cost-adjusted mean P&L/EV with a date-cluster 95% interval whose lower bound exceeds zero, acceptable calibration versus benchmarks, and no fragile single-bucket/date concentration.

## Artifacts

- `configs/EXP-20260903-chicago-paper-cohort.json`
- append-only daily raw/processed run paths
- daily data-quality summaries
- aggregate pilot report after 14 scheduled dates or an explicit early safety/data stop

## Update log

### 2026-09-03 — Preregistered

- Cohort, fixed time, primary/benchmark models, paper decision rule, metrics and gates locked before the first scheduled snapshot.
- Next action: implement and fixture-test the quantile-preserving CDF without retrieving an outcome.

### 2026-09-03 — Quantile-preserving baseline contract passed

- Component decision `QUANTILE_BASELINE_CONTRACT_PASS`; focused 17/17, full 111/111 and scoped Ruff passed.
- Tail extension, anchor interpolation, repeated-quantile jumps, exhaustive mass, monotonic rejection and total-variation alignment are deterministic.
- Outcome-free prior-forecast replay gave Gaussian-versus-quantile TV `0.273812`, confirming material model risk before any outcome comparison.
- Both models remain separately tracked; neither may be selected post-hoc.
- Next action: run scheduled snapshot 1 at 11:00 UTC ±15 minutes for target Sep 4.

### 2026-09-03 — Pre-data schedule amendment

- User requested moving the daily decision time one hour earlier before snapshot 1 or any cohort price/forecast observation.
- Decision time changed from 12:00 UTC to 11:00 UTC (14:00 Europe/Istanbul), retaining the same ±15-minute tolerance.
- Dates, models, paper rule, metrics and every acceptance/stop threshold are unchanged.
- This is a prospective amendment, not a post-result timing selection.

## Decision log

### PCD-0001 — 2026-09-03 — Use a short fixed-time pilot before a 30-day claim sample

- Decision: Schedule 14 dates with a minimum 10 eligible observations, then apply a resource-allocation gate.
- Rationale: This exposes operational and model failures quickly while explicitly preventing a small sample from becoming an edge claim.

### PCD-0002 — 2026-09-03 — Preserve NBM quantiles nonparametrically

- Decision: Primary probabilities use a fixed piecewise-linear CDF through published quantiles; Gaussian remains a benchmark.
- Rationale: The first live slice showed material disagreement between NBM's reported quantiles and a Gaussian fitted only to mean/sd.

### PCD-0003 — 2026-09-03 — Fix one paper decision per model/day

- Decision: Highest adjusted edge, minimum 3pp after fee and 2pp haircut, `$10` ask-depth, at most one position.
- Rationale: This limits multiple-testing and correlated exposure while retaining explicit no-trade observations.

### PCD-0004 — 2026-09-03 — Move the fixed snapshot to 11:00 UTC before cohort start

- Decision: Use 11:00 UTC ±15 minutes for every planned date.
- Evidence at decision time: No cohort snapshot had been taken; the change was requested for operator convenience.
- Consequence: The entire cohort uses the earlier time. A later timing change requires a new cohort version rather than mixing decision times.
