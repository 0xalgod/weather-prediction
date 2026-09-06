# EXP-20260907-us-nbm-station-coverage-v2

## Status

`PASSED` — frozen-object corrective evaluation completed on 2026-09-07.

## Hypothesis

The two KDEN blocks in the frozen 2026-05-14 07Z NBM object are complete byte-identical duplicates. Exact canonicalization should recover 36/36 station-date rows without changing forecast values or thresholds.

## Frozen data and method

Reuse the three immutable full objects from v1; do not download replacements. A block begins at its matching station header and ends immediately before the next generic NBM station header, or at EOF. Record every matching block's offset, byte length, and SHA-256.

One occurrence is accepted unchanged. Multiple occurrences are accepted only if every complete block has identical bytes and identical hashes; the first copy becomes canonical. Missing or conflicting copies are hard failures.

## Gates

All 12 station regimes and all three locked dates must produce 36/36 complete f41 feature rows. Required-field coverage must be 100%, temporal leakage zero, and conflicting duplicate count zero. These are unchanged in substance from v1; exact-identical source duplication is separated from duplicate logical station-date rows.

## Boundary

This is parser/data-quality evidence only. It does not validate NBM MaxT timezone semantics, predictive accuracy, executable EV, P&L, or live trading.

## Result

All 36/36 station-date rows passed with 100% required-field coverage, zero temporal leakage, zero conflicting duplicates, and zero errors. The two KDEN blocks were each 3,684 bytes at offsets 14,960,801 and 14,964,485. Both had SHA-256 `9783b1bfeec618de06cd863ee94cdafff3169051a6dde083b241f0a847dcf30d`, proving exact equality before canonicalization.

The station-content feasibility gate therefore passed. The next gate is city-local-day versus NBM f41 MaxT semantic alignment; no predictive or economic claim is made yet.
