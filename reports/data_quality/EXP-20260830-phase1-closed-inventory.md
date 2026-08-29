# EXP-20260830 — Phase 1 corrected closed inventory

**Data cut-off:** 2026-08-29T21:56:16Z (2026-08-30 Europe/Istanbul)
**Dataset version:** Corrected local Gamma run `20260829T215446Z`
**Code/config version:** Historical-identity contract at/after commit `522d06f`
**Covered markets:** Complete keyset traversal for `tag_slug=highest-temperature&closed=true`
**Status:** `COMPLETE`

## 1. Objective

Rerun the complete closed highest-temperature inventory after separating historical identifier integrity from current order-book eligibility, then measure market identity and settlement-field coverage.

## 2. Run integrity

| Metric | Result |
|---|---:|
| Keyset pages | 83 |
| Source events | 8,222 |
| Duplicate event IDs | 0 |
| Unique city labels | 54 |
| Nested market rows | 89,536 |
| Earliest event end | 2025-12-30T12:00:00Z |
| Latest event end | 2026-08-29T12:00:00Z |
| Raw envelope files | 83 |
| Raw envelope disk usage | 370 MB |

Corrected summary checksum:

```text
6558b9bd9608c7d71fce07e20651f642767208fd95f2a8d518c6de306ca62102  closed-summary-20260830-v2.json
```

The event/market/page/date counts exactly match the first run, providing a reproducibility check across two independent live traversals.

## 3. Corrected normalization results

| Metric | Result |
|---|---:|
| Market rows | 89,536 |
| Identifier-complete market rows | 89,514 |
| Identifier-incomplete market rows | 22 |
| Identifier-complete rate | 99.9754% |
| Historical outcome-token rows | 179,028 |
| Currently book-eligible rows | 0 |
| Past-end-date quality flags | 89,536 |

The 179,028 outcome rows equal two binary outcomes for every identifier-complete market. The zero current-book-eligible result is expected for a closed-history query and no longer suppresses historical identity.

Reason codes are non-exclusive:

| Reason | Count |
|---|---:|
| `EVENT_END_DATE_PASSED` | 89,536 |
| `MISSING_CONDITION_ID` | 22 |
| `MISSING_CLOB_TOKEN_IDS` | 22 |
| `INVALID_OUTCOME_TOKEN_JSON` | 22 |
| `NON_BINARY_BUCKET_MARKET` | 22 |

## 4. Settlement-field coverage

| Field condition | Count | Coverage |
|---|---:|---:|
| Events with non-empty `resolutionSource` | 7,583 / 8,222 | 92.2282% |
| Events with `automaticallyResolved=true` | 8,106 / 8,222 | 98.5892% |
| Events with non-empty `closedTime` | 8,165 / 8,222 | 99.3067% |
| Markets with condition ID | 89,514 / 89,536 | 99.9754% |
| Markets with non-empty CLOB token array | 89,514 / 89,536 | 99.9754% |
| Markets with non-empty `outcomePrices` | 89,514 / 89,536 | 99.9754% |
| Markets with `umaResolutionStatus=resolved` | 89,456 / 89,536 | 99.9107% |

Settlement-relevant fields are broadly present but not complete. The missing populations are material for strict provenance:

- 639 events lack a non-empty event-level resolution source.
- 116 events are not marked automatically resolved.
- 57 events lack event-level close time.
- 22 markets lack condition/token/outcome-price identity.
- 80 markets are not marked UMA-resolved.

These categories may overlap and require grouped reason analysis before exclusion.

## 5. Historical depth

The observed closed event end-date range is approximately eight months, from 2025-12-30 through 2026-08-29. This exceeds the minimum 20-event manual sample but is shorter than the preferred 365-day model-calibration period.

Gamma event history depth does not establish forecast archive depth. The latter remains a separate Phase 4 gate.

## 6. Storage finding

One full closed metadata traversal consumed approximately 370 MB as immutable envelopes. The corrective rerun intentionally created a second immutable run rather than overwriting the first, so local raw storage now includes both runs.

Before scheduled collection, the project must define:

- content-addressed deduplication or manifest references,
- compression policy,
- retention tiers,
- normalized projection storage,
- reproducibility rules for repeated identical payloads.

No raw run will be deleted as part of this experiment without an explicit retention decision.

## 7. Observed, inferred and unknown

### Observed

- Closed history is accessible through 83 keyset pages with no duplicate event IDs in the run.
- Identifier completeness is high but not 100%.
- Resolution and settlement metadata are present at high but imperfect coverage.
- The normalized historical outcome-token mapping is reproducible after the contract correction.

### Inferred

- Gamma can support a large historical event/market identity registry.
- A strict retained dataset needs explicit missing-source and unresolved-status classifications rather than wholesale acceptance.
- Repeated full snapshots are storage-expensive without content-addressed deduplication/compression.

### Unknown

- Whether missing event-level resolution sources can be recovered from market description, market-level source, UI, or related series.
- Whether non-UMA-resolved statuses represent invalid, pending, cancelled, or schema variants.
- Exact winning-token inference reliability from `outcomePrices` across all markets.
- Manual reconciliation accuracy against source pages and Polymarket UI.

## 8. Decision

The corrected closed-inventory substep passes.

Phase 1 remains `IN_PROGRESS` because:

- critical identifier/rule integrity has not reached the registered 100% retained-sample gate,
- missing settlement/source categories are not classified,
- manual reconciliation of at least 20 events is pending,
- the final normalized inventory/report is not complete.

## 9. Next action

Build deterministic missingness/reason cohorts for the 639 no-source events, 80 non-UMA-resolved markets, 57 no-close-time events and 22 identity-incomplete markets. Select a stratified 20-event manual reconciliation sample that includes both clean and anomalous cohorts.
