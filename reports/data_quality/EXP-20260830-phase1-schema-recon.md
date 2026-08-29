# EXP-20260830 — Phase 1 Gamma schema reconnaissance

**Data cut-off:** 2026-08-30
**Dataset version:** Live public API reconnaissance; no retained research dataset yet
**Code/config version:** Shell-based read-only spike on branch `feat/project-bootstrap`
**Covered markets:** First keyset page for active/not-closed Polymarket Weather and Highest Temperature events
**Status:** `COMPLETE`

## 1. Objective

Identify a reproducible, public, read-only discovery surface for Polymarket daily maximum-temperature bucket events before implementing the production ingestion client.

This step evaluates tag identity, endpoint pagination, response shape, market/outcome identifiers, and obvious filtering failure modes. It does not claim full discovery coverage.

## 2. Official sources

- List events: <https://docs.polymarket.com/api-reference/events/list-events>
- Keyset event pagination: <https://docs.polymarket.com/api-reference/events/list-events-keyset-pagination>
- Get tag by slug: <https://docs.polymarket.com/api-reference/tags/get-tag-by-slug>
- Get order book: <https://docs.polymarket.com/api-reference/market-data/get-order-book>

## 3. Read-only probes

The following public Gamma surfaces were inspected without authentication:

```text
GET /tags/slug/weather
GET /tags/slug/temperature
GET /tags/slug/highest-temperature
GET /events?tag_id=84&closed=false&limit=500&order=endDate&ascending=true
GET /events/keyset?tag_id=84&closed=false&limit=500&order=endDate&ascending=true
GET /events/keyset?tag_slug=highest-temperature&closed=false&limit=500&order=endDate&ascending=true
```

Raw responses were held in `/private/tmp` for schema reconnaissance and were not committed as a dataset. Production ingestion will use the repository's immutable raw envelope and checksums.

## 4. Tag findings

| Tag | ID | Observed role | Discovery decision |
|---|---:|---|---|
| `weather` | 84 | Broad parent category containing maximum/minimum temperature, rain, drought, and other weather events | Useful cross-check; too broad as primary filter |
| `temperature` | 104615 | Returned only two active/not-closed events in the probe and did not represent the daily MaxT universe | Reject as primary discovery filter |
| `highest-temperature` | 104596 | First keyset page contained 100 events and every observed title matched `Highest temperature in ...` | Use as primary discovery filter, with structural validation |

Tag labels cannot be assumed from the generic `/tags` first page. Tag-by-slug is the authoritative discovery bootstrap used in this spike.

## 5. Pagination findings

- Both the legacy list query and keyset query returned 100 records despite requesting `limit=500` in the observed calls.
- The keyset response included `events` and a non-null `next_cursor`.
- Full coverage therefore requires cursor iteration until the terminal cursor, not a single response.
- Offset pagination must not be mixed with keyset pagination.
- Ordering by `endDate,id` semantics must be tested through repeated pages; the cursor remains opaque.

## 6. First-page measurements

The first `weather` keyset page contained:

- 100 total weather events,
- 36 titles beginning with `Highest temperature in`,
- 33 unique city labels within those 36 events,
- 396 nested binary market rows across the 36 daily maximum-temperature events,
- 396 market rows with `enableOrderBook=true`,
- 396 market rows with `feesEnabled=true`,
- 44 market rows missing both `conditionId` and `clobTokenIds`.

The 44 missing-identifier rows correspond to four older May events with 11 bucket markets each in this first-page sample. This relationship is a preliminary observation and must be verified programmatically in the production spike.

## 7. Identifier and schema findings

One observed NYC daily maximum-temperature event demonstrated the expected hierarchy:

```text
event
└── 11 bucket markets
    └── each market has binary Yes/No outcomes and two CLOB token IDs
```

Observed event fields included:

- event `id`, `title`, `slug`, `endDate`, `active`, `closed`, `resolutionSource`, `tags`,
- `enableNegRisk=true` and `negRisk=true`,
- 11 nested bucket markets.

Observed nested market fields included:

- market `id`, `question`, `conditionId`, `slug`, `groupItemTitle`,
- JSON-encoded string fields `outcomes`, `outcomePrices`, and `clobTokenIds`,
- `enableOrderBook`, `orderPriceMinTickSize`, `orderMinSize`,
- `feesEnabled` and a structured `feeSchedule`,
- `active`, `closed`, and negative-risk metadata.

The NYC example exposed an official `resolutionSource` URL containing station code `KLGA`. This confirms that station evidence may be available at event level, but station parsing and correctness remain Phase 2 work.

## 8. Critical filtering finding

`active=true` and `closed=false` are not sufficient to identify currently tradeable or temporally relevant markets.

The observed active/not-closed response on 2026-08-30 included events with `endDate` in May 2026 and nested markets missing CLOB identifiers. Production discovery must therefore separate:

1. qualifying contract family,
2. lifecycle flags,
3. end-date relevance,
4. required identifier completeness,
5. order-book availability.

Stale or incomplete records must be retained with exclusion reasons for survivorship analysis rather than silently dropped.

## 9. Preliminary discovery rule

The next implementation will use:

1. tag-by-slug resolution for `highest-temperature`,
2. keyset pagination with the opaque cursor,
3. structural title and nested-market validation,
4. lifecycle and date fields recorded without trusting them as sole filters,
5. explicit identifier-quality classification,
6. raw-response checksums and UTC request/receipt timestamps.

The filter is preliminary until every page and a recent closed/resolved sample are reconciled.

## 10. Data-quality consequences

- JSON-encoded array strings require strict parsing and length checks.
- Each binary market should normally map two outcome labels to two CLOB token IDs; mismatches must fail normalization.
- A daily bucket event is not one CLOB market; it is an event containing multiple binary bucket markets.
- Negative-risk metadata must be preserved at event and market level.
- Fee metadata must be versioned per market rather than hard-coded globally.
- Missing identifiers require an explicit exclusion reason and cannot enter order-book collection.

## 11. Limitations

- Only the first keyset page was measured.
- No closed/resolved pagination was completed.
- No REST `/book` call was made in this step.
- No raw response was promoted to a versioned dataset.
- No manual sample of 20 events was completed.
- No discovery coverage percentage can yet be claimed.
- API rate-limit and retry behavior were not stress-tested.

## 12. Decision

The schema reconnaissance step passes its narrow objective.

- Primary filter candidate: `highest-temperature` tag, ID `104596`.
- Pagination method: keyset cursor iteration.
- General `weather` tag: cross-check only.
- `temperature` tag: rejected as primary filter.
- Phase 1 remains `IN_PROGRESS` because full pagination, normalized schema, fixtures, tests, closed/resolved coverage, and manual reconciliation remain pending.

## 13. Next action

Implement `src/weather_quant/ingestion/polymarket_markets.py` using standard-library HTTP/JSON support, immutable raw envelopes, keyset pagination, strict JSON-array parsing, and explicit exclusion reasons. Add sanitized fixtures and contract tests before querying the full result set.
