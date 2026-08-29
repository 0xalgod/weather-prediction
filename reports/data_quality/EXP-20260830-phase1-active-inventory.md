# EXP-20260830 — Phase 1 active/not-closed inventory

**Data cut-off:** 2026-08-29T21:48:44Z (2026-08-30 Europe/Istanbul)
**Dataset version:** Local prospective Gamma inventory run `20260829T214842Z`
**Code/config version:** `scripts/discover_polymarket_markets.py`, `configs/polymarket_discovery.json`
**Covered markets:** Complete keyset traversal for `tag_slug=highest-temperature&closed=false`
**Status:** `COMPLETE`

## 1. Objective

Execute the versioned discovery contract against every active/not-closed highest-temperature keyset page, preserve immutable raw envelopes, normalize the complete response, and quantify coverage and exclusion reasons.

## 2. Method

The collector executed:

```text
GET /events/keyset
tag_slug=highest-temperature
closed=false
order=endDate
ascending=true
limit=500
```

The server returned 100 records on page 1 despite the requested size, followed by 36 records on page 2 and a terminal cursor. The client followed only the opaque `next_cursor` and rejected cursor loops by contract.

Raw envelopes were written beneath:

```text
data/raw/polymarket_gamma/closed=false/run=20260829T214842Z/
```

Raw contents remain Git-ignored. This report and the versioned collector are the committed evidence index.

## 3. Run integrity

| Metric | Result |
|---|---:|
| Keyset pages | 2 |
| Source events | 136 |
| Duplicate event IDs | 0 |
| Raw envelope files | 2 |
| Raw envelope disk usage | 6.6 MB |
| First event end timestamp | 2026-05-20T12:00:00Z |
| Last event end timestamp | 2026-08-31T12:00:00Z |

Local envelope file checksums:

```text
a16261944e51bd0641d111d38e63aae9cf8e95ee0d58bddaf845d02e77b8be5e  page-00001-d4538887330b.json
5b70f1d4540efc71bfc28a0fb4cd36024e89f3cf122632ec9ba2cfd37832b0c8  page-00002-e0daea3537ec.json
```

The filename hash prefix refers to the source-response content checksum inside the envelope. The listed file checksum covers the serialized envelope and is therefore intentionally different.

## 4. Coverage results

| Metric | Result |
|---|---:|
| Events | 136 |
| Unique city labels | 51 |
| Nested bucket markets | 1,496 |
| Normalized binary outcomes | 2,200 |
| Temporally relevant events at run time | 100 |
| Eligible markets for future book collection | 1,100 |
| Excluded markets | 396 |

The 1,100 eligible markets equal 100 current events with 11 binary bucket markets each. Eligibility here means only that the market passed the registered identifier/book/date contract. It does not prove a non-empty order book, liquidity, or tradeability.

## 5. Exclusion results

Reason codes are non-exclusive:

| Reason | Count |
|---|---:|
| `EVENT_END_DATE_PASSED` | 396 |
| `MISSING_CONDITION_ID` | 44 |
| `MISSING_CLOB_TOKEN_IDS` | 44 |
| `INVALID_OUTCOME_TOKEN_JSON` | 44 |
| `NON_BINARY_BUCKET_MARKET` | 44 |

All 396 excluded rows belonged to events whose `endDate` preceded the collector's UTC start time. A subset of 44 also lacked usable condition/token data. The generic invalid/non-binary codes arise because the missing `clobTokenIds` value cannot establish a two-token mapping; they do not imply that the market question itself was designed as non-binary.

## 6. City coverage

The run contained 51 unique city labels. Event counts ranged from 2 to 4:

- Hong Kong: 4 events.
- 34 city labels: 3 events each.
- 16 city labels: 2 events each.

The observed labels include US and non-US cities. This is discovery coverage only; no city passes the project's source/station/forecast/observation score yet.

## 7. Findings

### Observed

- Full active/not-closed traversal currently requires two keyset pages.
- The endpoint returns stale records even under `closed=false`.
- All 100 temporally relevant events had 11 nested markets that passed the current identifier/book metadata contract.
- The discovery universe is much wider than the planned initial 3–5 cities.
- The raw response size is nontrivial: two metadata pages consumed 6.6 MB as envelopes.

### Inferred

- A current inventory can be collected reliably through keyset pagination.
- `closed=false` must be treated as a source lifecycle attribute, not a current-market filter.
- Storage estimates must be measured rather than inferred from event counts because nested Gamma payloads contain extensive metadata.

### Unknown

- Closed/resolved history depth and page count.
- Manual rule and identifier reconciliation accuracy.
- Actual `/book` success, depth, staleness and liquidity for the 1,100 eligible tokens/markets.
- Whether every city uses stable resolution stations and sources.

## 8. Limitations

- The run queried only `closed=false`.
- Temporal relevance used event `endDate` versus collection time; contract-specific trading cutoff semantics remain unresolved.
- No live order-book endpoint was called.
- No market was manually reconciled against the Polymarket UI or resolution source.
- Counts describe nested binary markets, not independent event outcomes or trading opportunities.

## 9. Decision

The full active-inventory substep passes.

Phase 1 remains `IN_PROGRESS` because the registered exit criteria also require closed/resolved coverage, at least 20 manual reconciliations, a durable normalized inventory artifact, and a final discovery coverage report.

## 10. Next action

Run the same keyset collector with `closed=true`, measure historical depth and payload/storage scale, and inspect settlement/resolution fields before selecting the manual reconciliation sample.
