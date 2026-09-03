# NBM quantile-preserving baseline v1

**Decision:** `QUANTILE_BASELINE_CONTRACT_PASS`  
**Outcome used:** No  
**Focused tests:** 17/17  
**Full suite:** 111/111

The prospective paper cohort's primary probability baseline is implemented before its first scheduled snapshot. It constructs the exact preregistered piecewise-linear CDF through NBM p10/p25/p50/p75/p90, extends finite tails by the locked slope rule, treats repeated quantiles as explicit right-continuous probability jumps and applies half-degree integer bucket boundaries.

Contract tests cover anchor values, finite tails, repeated quantiles, exhaustive probability sum, nonmonotonic-input rejection and aligned total-variation comparison. Scoped Ruff passes.

An outcome-free replay on the prior live forecast produced total variation `0.2738` versus the Gaussian model. The quantile baseline assigns substantially more mass to `86-87°F` and `94-95°F`, less to `90-93°F`, and zero beyond its locked finite tail endpoints. This is not proof that the quantile baseline is correct; it proves that distribution choice materially changes the apparent edge and must be evaluated prospectively rather than selected after outcomes.

Both models will therefore be preserved independently in every cohort record. The first eligible snapshot window is 2026-09-03 12:00 UTC ±15 minutes.
