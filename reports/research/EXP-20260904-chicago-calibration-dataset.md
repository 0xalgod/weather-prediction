# Chicago expanded calibration dataset gate

**Decision:** `CALIBRATION_DATASET_FAIL`  
**Training performed:** no

## Result

All source downloads completed: 30 prior objects were checksum-verified and reused, 84 new objects were downloaded, and no transport failure remained. The accepted source set is 3,958,130,429 bytes.

The locked dataset gate nevertheless failed:

| Metric | Observed | Required |
|---|---:|---:|
| Universe | 114 | 114 |
| Eligible | 112 (98.25%) | ≥99% |
| Available OOS after 60 train | 52 | ≥53 |
| Publication-proxy leakage | 1 | 0 |

Two dates were excluded rather than repaired:

- 2026-05-06 used the 2026-05-05 07Z forecast, which identifies itself as NBM v4.3 rather than the locked v5.0 regime.
- 2026-05-08's 07Z object has HTTP Last-Modified 13:16:33 UTC, after the locked prior-day 11:00 UTC decision time.

No alternative cycle, later file, replacement date, imputation or threshold change was applied. Because a registered data gate failed, walk-forward calibration was not run under this experiment version.

## Corrective direction

A new explicitly post-hoc experiment may narrow the consistent v5.0 universe to dates beginning 2026-05-07, preserve 2026-05-08 as missing, keep 60 initial training events and evaluate the resulting 52 OOS events. This would be a new gate and cannot retroactively convert this failed experiment into a pass.
