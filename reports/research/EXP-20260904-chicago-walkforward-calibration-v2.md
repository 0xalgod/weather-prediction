# Chicago walk-forward calibration v2 — result

**Decision:** `NO_STRONG_CALIBRATION_EVIDENCE`  
**Design:** post-hoc corrective, registered before expanded-sample scores  
**OOS:** 52 dates, 2026-07-08 through 2026-08-28  
**Trading authorization:** none

## What was trained

The first 60 eligible dates formed the initial history. For each following date, the shift/spread grid was selected again using only prior outcomes, then one genuinely future bucket was scored. Training history expanded from 60 to 111 events. No random split or future outcome was used.

## OOS result

Lower scores are better.

| Model | Raw log loss | Calibrated log loss | Relative change | Raw Brier | Calibrated Brier | Practical gate |
|---|---:|---:|---:|---:|---:|---|
| Gaussian | 1.4628 | 1.4528 | 0.69% better | 0.7343 | 0.7574 | Fail |
| Quantile | **1.4102** | 1.4668 | 4.02% worse | **0.7335** | 0.7596 | Fail |

Gaussian calibration reduced mean log loss by only 0.69%, below the locked 2% threshold, and worsened Brier by `+0.0232`. Its paired calibrated-minus-raw log-loss CI was `[-0.1280, +0.1252]`.

Quantile calibration worsened log loss by 4.02% and Brier by `+0.0261`; its paired CI was `[-0.0469, +0.1625]`.

Neither model passed practical or strong-evidence gates. The most common fitted values were a small negative temperature shift; no shift hit the ±5°F grid boundary. This suggests the failure is not merely a grid-range truncation.

## Decision

Simple global shift/spread recalibration should not replace the raw NBM distributions. Raw quantile is the best tested forecast baseline on this OOS stream, but its advantage is a weather-probability result—not evidence that Polymarket is mispriced.

Further model complexity should not be selected on these same 52 OOS dates. The sensible next evidence is prospective Day 1 settlement/P&L reconciliation and additional fixed-time market snapshots. A future modeling experiment needs a fresh temporal regime or pre-registered covariates and a new untouched test period.
