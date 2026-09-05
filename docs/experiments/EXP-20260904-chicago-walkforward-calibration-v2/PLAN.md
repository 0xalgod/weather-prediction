# EXP-20260904 — Chicago walk-forward calibration v2

**Status:** `FAILED`
**Design:** `POST_HOC_CORRECTIVE_BEFORE_MODEL_SCORES`

## Why a new experiment

The original registered dataset gate failed before model fitting because the first target used NBM v4.3 and another forecast was published after the decision cutoff. The failed experiment remains failed. This v2 design is registered after those data-quality facts were observed but before any 114-date calibration fit or OOS score was calculated.

## Locked sample and split

- Use the checksum-locked expanded dataset result.
- Start on 2026-05-07, the first target whose prior-day 07Z source identifies itself as NBM v5.0.
- Require source-row eligibility; 2026-05-08 remains excluded for late publication and 2026-06-18 remains an absent market date.
- Exact eligible count: 112.
- First 60 eligible dates: initial training.
- Remaining 52 eligible dates: expanding-window OOS, refit before every event using past events only.

## Models, grid and metrics

No model choice was changed. Raw/calibrated Gaussian and raw/calibrated quantile use the original shift `−5..+5°F` by `0.5°F` and spread `{0.75, 1, 1.25}` grid. Train log loss selects parameters with the original deterministic tie-break.

Primary and secondary metrics, probability floor, 10,000 paired bootstrap samples and seed remain unchanged.

Practical improvement still requires at least 2% relative OOS log-loss improvement and non-worse Brier versus the corresponding raw model. Strong evidence still requires the paired log-loss difference CI upper bound below zero.

## Claim boundary

This post-hoc correction reduces evidential strength and will be labelled as such in all results. It can establish whether simple calibration is promising, not a trading edge. There is no market-price, EV, fill or order calculation.

## 2026-09-05 result

- Contract passed: 112 eligible, 60 initial train, 52 expanding-window OOS, train histories 60–111, finite scores and exact probability sums.
- Gaussian calibration log loss improved only 0.69% (<2%) and Brier worsened `+0.0232`; paired CI crossed zero.
- Quantile calibration log loss worsened 4.02% and Brier worsened `+0.0261`; paired CI crossed zero.
- Neither practical nor strong-evidence gate passed. Decision: `NO_STRONG_CALIBRATION_EVIDENCE`.
- Raw quantile remains the best tested forecast baseline. No trading/market/EV claim is made.
